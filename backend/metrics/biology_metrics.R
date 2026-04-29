# Calculate biology mechanism metrics from an enrichment parquet file.
# Usage: Rscript biology_metrics.R <enrichment.parquet> [GO|KEGG]

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

safe_min_positive <- function(values) {
  values <- suppressWarnings(as.numeric(values))
  values <- values[is.finite(values) & values > 0]
  if (length(values) == 0) {
    return(NA_real_)
  }
  min(values)
}

empty_metrics <- function(database) {
  list(
    database = database,
    significant_pathway_count = 0L,
    core_pathway_score = 0.0,
    core_pathway = NULL,
    core_cluster = NULL,
    core_category = NULL,
    core_p_value = NULL,
    core_adjusted_p = NULL,
    total_pathways = 0L
  )
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  emit_json(list(error = "Usage: Rscript biology_metrics.R <enrichment.parquet> [GO|KEGG]"))
  quit(save = "no", status = 1)
}

tryCatch(
  {
    input_path <- args[[1]]
    database <- if (length(args) >= 2) toupper(args[[2]]) else "GO"
    if (!file.exists(input_path)) {
      stop(paste0("enrichment parquet not found: ", input_path))
    }

    enrichment_df <- as.data.frame(arrow::read_parquet(input_path))
    if (nrow(enrichment_df) == 0) {
      emit_json(empty_metrics(database))
      quit(save = "no", status = 0)
    }

    required_columns <- c("cluster", "Term", "P_value", "Adjusted_P", "Category")
    missing_columns <- setdiff(required_columns, names(enrichment_df))
    if (length(missing_columns) > 0) {
      stop(paste0("enrichment parquet missing columns: ", paste(missing_columns, collapse = ", ")))
    }

    enrichment_df$P_value <- suppressWarnings(as.numeric(enrichment_df$P_value))
    enrichment_df$Adjusted_P <- suppressWarnings(as.numeric(enrichment_df$Adjusted_P))

    significance_p <- enrichment_df$Adjusted_P
    significance_p[!is.finite(significance_p)] <- enrichment_df$P_value[!is.finite(significance_p)]
    significant <- is.finite(significance_p) & significance_p < 0.05

    if (!any(significant)) {
      result <- empty_metrics(database)
      result$total_pathways <- as.integer(nrow(enrichment_df))
      emit_json(result)
      quit(save = "no", status = 0)
    }

    significant_df <- enrichment_df[significant, , drop = FALSE]
    significant_p <- significance_p[significant]
    best_index <- which.min(significant_p)
    best_row <- significant_df[best_index, , drop = FALSE]
    best_p <- safe_min_positive(significant_p[best_index])
    score <- if (is.na(best_p)) 0.0 else -log10(best_p)

    emit_json(list(
      database = database,
      significant_pathway_count = as.integer(nrow(significant_df)),
      core_pathway_score = as.numeric(score),
      core_pathway = as.character(best_row$Term[[1]]),
      core_cluster = as.integer(best_row$cluster[[1]]),
      core_category = as.character(best_row$Category[[1]]),
      core_p_value = safe_min_positive(best_row$P_value),
      core_adjusted_p = safe_min_positive(best_row$Adjusted_P),
      total_pathways = as.integer(nrow(enrichment_df))
    ))
  },
  error = function(e) {
    emit_json(list(error = conditionMessage(e)))
    quit(save = "no", status = 1)
  }
)
