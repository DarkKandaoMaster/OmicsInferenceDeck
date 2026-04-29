# Core differential statistics.
# Usage: Rscript differential.R <input.parquet> <volcano.parquet> <heatmap.parquet>

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

to_json <- function(value) {
  if (is.null(value) || length(value) == 0) {
    return("[]")
  }
  if (is.list(value) && is.null(names(value))) {
    return(paste0("[", paste(vapply(value, to_json, character(1)), collapse = ","), "]"))
  }
  if (is.list(value)) {
    pairs <- vapply(
      names(value),
      function(name) paste0(json_escape(name), ":", to_json(value[[name]])),
      character(1)
    )
    return(paste0("{", paste(pairs, collapse = ","), "}"))
  }
  if (length(value) != 1) {
    return(to_json(as.list(value)))
  }
  if (is.na(value)) {
    return("null")
  }
  if (is.numeric(value) || is.integer(value)) {
    value <- as.numeric(value)
    if (!is.finite(value)) {
      return("null")
    }
    return(format(value, digits = 15, scientific = TRUE, trim = TRUE))
  }
  if (is.logical(value)) {
    return(ifelse(isTRUE(value), "true", "false"))
  }
  json_escape(value)
}

emit_json <- function(payload) {
  cat(paste0(to_json(payload), "\n"))
}

empty_volcano <- function(cluster_id, genes) {
  data.frame(
    cluster = cluster_id,
    gene = as.character(genes),
    logFC = 0.0,
    t_pvalue = 1.0,
    negLog10P = 0.0,
    stringsAsFactors = FALSE
  )
}

safe_t_pvalue <- function(group_a, group_b) {
  tryCatch(
    {
      p_value <- stats::t.test(group_a, group_b, var.equal = FALSE)$p.value
      if (is.na(p_value) || !is.finite(p_value)) 1.0 else max(p_value, 0.0)
    },
    error = function(e) 1.0
  )
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  emit_json(list(error = "Usage: Rscript differential.R <input.parquet> <volcano.parquet> <heatmap.parquet>"))
  quit(save = "no", status = 1)
}

tryCatch(
  {
    input_path <- args[[1]]
    volcano_path <- args[[2]]
    heatmap_path <- args[[3]]

    df <- as.data.frame(arrow::read_parquet(input_path))
    if (!("sample_name" %in% names(df)) || !("Cluster" %in% names(df))) {
      stop("input parquet must contain sample_name and Cluster columns")
    }

    genes <- setdiff(names(df), c("sample_name", "Cluster"))
    if (length(genes) < 1) {
      stop("input parquet must contain at least one feature column")
    }

    df$sample_name <- as.character(df$sample_name)
    df$Cluster <- suppressWarnings(as.integer(df$Cluster))
    if (any(is.na(df$Cluster))) {
      stop("Cluster column contains missing or non-integer values")
    }

    for (gene in genes) {
      df[[gene]] <- suppressWarnings(as.numeric(df[[gene]]))
    }

    clusters <- sort(unique(df$Cluster))
    volcano_frames <- list()
    top_genes <- character(0)

    for (cluster_id in clusters) {
      group_a <- df[df$Cluster == cluster_id, genes, drop = FALSE]
      group_b <- df[df$Cluster != cluster_id, genes, drop = FALSE]

      if (nrow(group_a) < 2 || nrow(group_b) < 2) {
        cluster_result <- empty_volcano(cluster_id, genes)
        volcano_frames[[length(volcano_frames) + 1]] <- cluster_result
        next
      }

      mean_a <- colMeans(group_a, na.rm = TRUE)
      mean_b <- colMeans(group_b, na.rm = TRUE)
      log_fc <- mean_a - mean_b
      p_values <- vapply(
        genes,
        function(gene) safe_t_pvalue(group_a[[gene]], group_b[[gene]]),
        numeric(1)
      )
      p_values[is.na(p_values) | !is.finite(p_values)] <- 1.0
      p_values <- pmax(p_values, 0.0)

      cluster_result <- data.frame(
        cluster = cluster_id,
        gene = as.character(genes),
        logFC = as.numeric(log_fc),
        t_pvalue = as.numeric(p_values),
        stringsAsFactors = FALSE
      )
      cluster_result$logFC[is.na(cluster_result$logFC) | !is.finite(cluster_result$logFC)] <- 0.0
      cluster_result$negLog10P <- -log10(cluster_result$t_pvalue + 1e-300)
      volcano_frames[[length(volcano_frames) + 1]] <- cluster_result

      significant <- cluster_result[cluster_result$t_pvalue < 0.05 & cluster_result$logFC > 0.5, , drop = FALSE]
      if (nrow(significant) > 0) {
        significant <- significant[order(-significant$logFC, significant$t_pvalue), , drop = FALSE]
        for (gene in head(significant$gene, 10)) {
          if (!(gene %in% top_genes)) {
            top_genes <- c(top_genes, gene)
          }
        }
      }
    }

    volcano_df <- if (length(volcano_frames) > 0) {
      do.call(rbind, volcano_frames)
    } else {
      data.frame(cluster = integer(), gene = character(), logFC = numeric(), t_pvalue = numeric(), negLog10P = numeric())
    }
    arrow::write_parquet(volcano_df, volcano_path)

    if (length(top_genes) > 0) {
      heatmap_df <- df[, c("sample_name", "Cluster", top_genes), drop = FALSE]
      for (gene in top_genes) {
        values <- heatmap_df[[gene]]
        std <- stats::sd(values, na.rm = TRUE)
        if (is.na(std) || !is.finite(std) || std == 0) {
          heatmap_df[[gene]] <- 0.0
        } else {
          scaled <- (values - mean(values, na.rm = TRUE)) / std
          scaled[is.na(scaled) | !is.finite(scaled)] <- 0.0
          heatmap_df[[gene]] <- scaled
        }
      }
      heatmap_df <- heatmap_df[order(heatmap_df$Cluster), , drop = FALSE]
      heatmap_df <- heatmap_df[, c("sample_name", "Cluster", top_genes), drop = FALSE]
    } else {
      heatmap_df <- data.frame(sample_name = character(), Cluster = integer())
    }
    arrow::write_parquet(heatmap_df, heatmap_path)

    emit_json(list(
      clusters = as.list(as.integer(clusters)),
      selected_cluster = if (length(clusters) > 0) as.integer(clusters[[1]]) else 0L,
      top_genes = as.list(top_genes),
      n_features = length(genes),
      n_top_genes = length(top_genes)
    ))
  },
  error = function(e) {
    emit_json(list(error = conditionMessage(e)))
    quit(save = "no", status = 1)
  }
)
