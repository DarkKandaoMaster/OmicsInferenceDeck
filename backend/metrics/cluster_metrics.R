# Calculate clustering metrics for a persisted cluster_result.parquet file.
# Usage: Rscript cluster_metrics.R <parquet_file>

suppressPackageStartupMessages({
  library(arrow)
  library(cluster)
  library(clusterCrit)
})

metric_keys <- c("silhouette", "silhouette_cluster", "calinski", "davies", "dunn", "xb", "s_dbw")

fallback_metrics <- function() {
  values <- as.list(rep(-1, length(metric_keys)))
  names(values) <- metric_keys
  values
}

json_escape <- function(value) {
  value <- as.character(value)
  value <- gsub("\\", "\\\\", value, fixed = TRUE)
  value <- gsub("\"", "\\\"", value, fixed = TRUE)
  value <- gsub("\n", "\\n", value, fixed = TRUE)
  value <- gsub("\r", "\\r", value, fixed = TRUE)
  value <- gsub("\t", "\\t", value, fixed = TRUE)
  paste0("\"", value, "\"")
}

json_value <- function(value) {
  if (is.null(value) || length(value) == 0) {
    return("null")
  }
  if (is.numeric(value) || is.integer(value)) {
    value <- as.numeric(value[1])
    if (is.na(value) || !is.finite(value)) {
      return("null")
    }
    return(format(value, scientific = FALSE, trim = TRUE))
  }
  if (is.logical(value)) {
    return(ifelse(isTRUE(value), "true", "false"))
  }
  json_escape(value[1])
}

json_object <- function(values) {
  pairs <- vapply(
    names(values),
    function(name) paste0(json_escape(name), ":", json_value(values[[name]])),
    character(1)
  )
  paste0("{", paste(pairs, collapse = ","), "}")
}

emit_success <- function(metrics, n_samples, n_features) {
  cat(
    paste0(
      "{\"metrics\":", json_object(metrics),
      ",\"n_samples\":", json_value(n_samples),
      ",\"n_features\":", json_value(n_features),
      "}\n"
    )
  )
}

emit_error <- function(message) {
  cat(paste0("{\"error\":", json_escape(message), "}\n"))
}

round_or_null <- function(value) {
  if (is.null(value) || length(value) == 0) {
    return(NA_real_)
  }
  value <- as.numeric(value[1])
  if (is.na(value) || !is.finite(value)) {
    return(NA_real_)
  }
  round(value, 4)
}

compute_metric <- function(embeddings, labels, criterion, field_name) {
  score <- tryCatch(
    {
      clusterCrit::intCriteria(
        traj = embeddings,
        part = labels,
        crit = criterion
      )[[field_name]]
    },
    error = function(e) NA_real_
  )
  round_or_null(score)
}

compute_sklearn_silhouette <- function(embeddings, labels) {
  score <- tryCatch(
    {
      sil <- cluster::silhouette(labels, stats::dist(embeddings))
      mean(sil[, "sil_width"])
    },
    error = function(e) NA_real_
  )
  round_or_null(score)
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  emit_error("Usage: Rscript cluster_metrics.R <parquet_file>")
  quit(save = "no", status = 1)
}

tryCatch(
  {

    df <- suppressWarnings(suppressMessages(
      arrow::read_parquet(args[1], as_data_frame = TRUE)
    ))

    if (!("label" %in% names(df))) {
      stop("column 'label' is required")
    }

    emb_cols <- grep("^emb_", names(df), value = TRUE)
    n_samples <- nrow(df)
    n_features <- length(emb_cols)

    if (n_features < 1) {
      stop("at least one 'emb_' feature column is required")
    }

    labels <- suppressWarnings(as.integer(df$label))
    embeddings <- suppressWarnings(as.matrix(df[, emb_cols, drop = FALSE]))
    storage.mode(embeddings) <- "double"

    if (any(is.na(labels))) {
      stop("column 'label' contains missing or non-integer values")
    }
    if (any(!is.finite(embeddings))) {
      stop("'emb_' feature columns contain missing or non-numeric values")
    }

    n_clusters <- length(unique(labels))
    if (n_clusters < 2 || length(labels) <= n_clusters) {
      emit_success(fallback_metrics(), n_samples, n_features)
      quit(save = "no", status = 0)
    }

    labels <- as.integer(factor(labels))

    metrics <- list(
      silhouette = compute_sklearn_silhouette(embeddings, labels),
      silhouette_cluster = compute_metric(embeddings, labels, "Silhouette", "silhouette"),
      calinski = compute_metric(embeddings, labels, "Calinski_Harabasz", "calinski_harabasz"),
      davies = compute_metric(embeddings, labels, "Davies_Bouldin", "davies_bouldin"),
      dunn = compute_metric(embeddings, labels, "Dunn", "dunn"),
      xb = compute_metric(embeddings, labels, "Xie_Beni", "xie_beni"),
      s_dbw = compute_metric(embeddings, labels, "S_Dbw", "s_dbw")
    )

    emit_success(metrics, n_samples, n_features)
  },
  error = function(e) {
    emit_error(conditionMessage(e))
    quit(save = "no", status = 1)
  }
)
