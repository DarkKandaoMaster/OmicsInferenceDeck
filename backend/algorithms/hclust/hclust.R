suppressPackageStartupMessages({
  library(arrow)
})

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
  if (length(value) == 0) {
    return("null")
  }
  value <- as.numeric(value[1])
  if (is.na(value) || !is.finite(value)) {
    return("null")
  }
  format(value, scientific = FALSE, trim = TRUE, digits = 17)
}

json_string_vector <- function(values) {
  paste0("[", paste(vapply(values, json_escape, character(1)), collapse = ","), "]")
}

json_number_vector <- function(values) {
  paste0("[", paste(vapply(values, json_value, character(1)), collapse = ","), "]")
}

emit_success <- function(sample_names, labels, method, distance) {
  cat(
    paste0(
      "{\"status\":\"success\"",
      ",\"sample_names\":", json_string_vector(sample_names),
      ",\"labels\":", json_number_vector(labels),
      ",\"method\":", json_escape(method),
      ",\"distance\":", json_escape(distance),
      ",\"n_samples\":", json_value(length(sample_names)),
      "}\n"
    )
  )
}

emit_error <- function(message) {
  cat(paste0("{\"error\":", json_escape(message), "}\n"))
}

parse_positive_int <- function(value, default_value) {
  parsed <- suppressWarnings(as.integer(value))
  if (is.na(parsed) || parsed <= 0) {
    return(default_value)
  }
  parsed
}

matrix_from_parquet <- function(input_path) {
  df <- suppressWarnings(suppressMessages(
    arrow::read_parquet(input_path, as_data_frame = TRUE)
  ))

  if (!("sample_name" %in% names(df))) {
    stop("Saved omics parquet must contain a sample_name column.")
  }

  sample_names <- as.character(df$sample_name)
  feature_cols <- grep("^frame_[0-9]+__col_[0-9]+$", names(df), value = TRUE)
  if (length(feature_cols) == 0) {
    stop("Saved omics parquet does not contain frame_*__col_* feature columns.")
  }

  mat <- as.matrix(df[, feature_cols, drop = FALSE])
  storage.mode(mat) <- "double"
  rownames(mat) <- sample_names

  if (any(!is.finite(mat))) {
    stop("Saved omics data contains missing or non-numeric values. Please check upload alignment and input cleaning.")
  }
  mat
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  emit_error("Usage: Rscript hclust.R <omics_parquet> <n_clusters> [method] [distance]")
  quit(save = "no", status = 1)
}

tryCatch(
  {
    input_path <- args[1]
    n_clusters <- parse_positive_int(args[2], 3)
    method <- if (length(args) >= 3 && args[3] != "") args[3] else "ward.D2"
    distance <- if (length(args) >= 4 && args[4] != "") args[4] else "euclidean"

    if (!file.exists(input_path)) {
      stop(paste("Input parquet not found:", input_path))
    }

    valid_methods <- c("ward.D", "ward.D2", "single", "complete", "average", "mcquitty", "median", "centroid")
    if (!(method %in% valid_methods)) {
      stop(paste("Unsupported hclust method:", method))
    }

    valid_distances <- c("euclidean", "maximum", "manhattan", "canberra", "binary", "minkowski")
    if (!(distance %in% valid_distances)) {
      stop(paste("Unsupported dist method:", distance))
    }

    mat <- matrix_from_parquet(input_path)
    n_samples <- nrow(mat)
    if (n_samples < 2) {
      stop("Hclust requires at least two samples.")
    }
    if (n_clusters > n_samples) {
      stop("n_clusters cannot be greater than the number of samples.")
    }

    labels <- stats::cutree(
      stats::hclust(stats::dist(mat, method = distance), method = method),
      k = n_clusters
    )
    labels <- suppressWarnings(as.integer(labels))
    if (length(labels) != n_samples || any(is.na(labels))) {
      stop("Hclust returned invalid clustering labels.")
    }

    emit_success(rownames(mat), labels, method, distance)
  },
  error = function(e) {
    emit_error(conditionMessage(e))
    quit(save = "no", status = 1)
  }
)
