# Core GO/KEGG enrichment statistics from local GMT files.
# Usage: Rscript enrichment.R <database> <input.parquet> <output.parquet> <gmt_base_dir> [genes|volcano]

suppressPackageStartupMessages({
  library(arrow)
  library(clusterProfiler)
})

RESULT_COLUMNS <- c(
  "cluster",
  "Term",
  "P_value",
  "Adjusted_P",
  "Overlap",
  "Genes",
  "Gene_Count",
  "Category",
  "Rich_Factor"
)

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

empty_result <- function() {
  result <- data.frame(
    cluster = integer(),
    Term = character(),
    P_value = numeric(),
    Adjusted_P = numeric(),
    Overlap = character(),
    Genes = character(),
    Gene_Count = integer(),
    Category = character(),
    Rich_Factor = numeric(),
    stringsAsFactors = FALSE
  )
  result[, RESULT_COLUMNS, drop = FALSE]
}

gmt_files <- function(database, base_dir) {
  database <- toupper(database)
  if (database == "GO") {
    return(list(
      BP = file.path(base_dir, "GO_Biological_Process_2025.gmt"),
      CC = file.path(base_dir, "GO_Cellular_Component_2025.gmt"),
      MF = file.path(base_dir, "GO_Molecular_Function_2025.gmt")
    ))
  }
  if (database == "KEGG") {
    return(list(KEGG = file.path(base_dir, "KEGG_2026.gmt")))
  }
  stop("database must be GO or KEGG")
}

read_term2gene <- function(path) {
  if (!file.exists(path)) {
    stop(paste0("GMT file not found: ", path))
  }
  term2gene <- clusterProfiler::read.gmt(path)
  if (ncol(term2gene) < 2) {
    stop(paste0("invalid GMT file: ", path))
  }
  names(term2gene)[1:2] <- c("term", "gene")
  term2gene[, c("term", "gene"), drop = FALSE]
}

ratio_numerator <- function(value) {
  parts <- strsplit(as.character(value), "/", fixed = TRUE)[[1]]
  if (length(parts) != 2) {
    return(NA_real_)
  }
  suppressWarnings(as.numeric(parts[[1]]))
}

format_clusterprofiler_result <- function(cluster_id, category, result_df) {
  if (is.null(result_df) || nrow(result_df) == 0) {
    return(empty_result())
  }

  result_df <- result_df[result_df$pvalue < 0.05, , drop = FALSE]
  if (nrow(result_df) == 0) {
    return(empty_result())
  }
  result_df <- result_df[order(result_df$pvalue), , drop = FALSE]
  result_df <- head(result_df, 5)

  term_sizes <- vapply(result_df$BgRatio, ratio_numerator, numeric(1))
  hit_counts <- as.numeric(result_df$Count)
  rich_factor <- hit_counts / term_sizes
  rich_factor[is.na(rich_factor) | !is.finite(rich_factor)] <- 0.0

  data.frame(
    cluster = as.integer(cluster_id),
    Term = as.character(result_df$Description),
    P_value = as.numeric(result_df$pvalue),
    Adjusted_P = as.numeric(result_df$p.adjust),
    Overlap = paste0(hit_counts, "/", term_sizes),
    Genes = gsub("/", ";", as.character(result_df$geneID), fixed = TRUE),
    Gene_Count = as.integer(hit_counts),
    Category = as.character(category),
    Rich_Factor = as.numeric(rich_factor),
    stringsAsFactors = FALSE
  )[, RESULT_COLUMNS, drop = FALSE]
}

enrich_one_category <- function(cluster_id, query_genes, category, term2gene) {
  universe <- unique(as.character(term2gene$gene))
  query <- unique(intersect(as.character(query_genes), universe))
  if (length(query) < 3 || length(universe) < 1) {
    return(empty_result())
  }

  enrichment <- clusterProfiler::enricher(
    gene = query,
    universe = universe,
    TERM2GENE = term2gene,
    pvalueCutoff = 1,
    pAdjustMethod = "BH",
    qvalueCutoff = 1,
    minGSSize = 1,
    maxGSSize = 5000
  )
  format_clusterprofiler_result(cluster_id, category, as.data.frame(enrichment))
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 4) {
  emit_json(list(error = "Usage: Rscript enrichment.R <database> <input.parquet> <output.parquet> <gmt_base_dir> [genes|volcano]"))
  quit(save = "no", status = 1)
}

tryCatch(
  {
    database <- toupper(args[[1]])
    input_path <- args[[2]]
    output_path <- args[[3]]
    gmt_base_dir <- args[[4]]
    input_mode <- if (length(args) >= 5) tolower(args[[5]]) else "genes"

    input_df <- as.data.frame(arrow::read_parquet(input_path))
    if (input_mode == "volcano") {
      required_columns <- c("cluster", "gene", "t_pvalue", "logFC")
      missing_columns <- setdiff(required_columns, names(input_df))
      if (length(missing_columns) > 0) {
        stop(paste0("volcano parquet missing columns: ", paste(missing_columns, collapse = ", ")))
      }
      input_df$t_pvalue <- suppressWarnings(as.numeric(input_df$t_pvalue))
      input_df$logFC <- suppressWarnings(as.numeric(input_df$logFC))
      cluster_gene_df <- input_df[input_df$t_pvalue < 0.05 & input_df$logFC > 0.5, c("cluster", "gene"), drop = FALSE]
      cluster_gene_df <- cluster_gene_df[order(cluster_gene_df$cluster, input_df$t_pvalue[input_df$t_pvalue < 0.05 & input_df$logFC > 0.5]), , drop = FALSE]
    } else {
      cluster_gene_df <- input_df
    }

    if (!("cluster" %in% names(cluster_gene_df)) || !("gene" %in% names(cluster_gene_df))) {
      stop("input parquet must contain cluster and gene columns")
    }

    cluster_gene_df$cluster <- suppressWarnings(as.integer(cluster_gene_df$cluster))
    cluster_gene_df$gene <- as.character(cluster_gene_df$gene)
    cluster_gene_df <- cluster_gene_df[!is.na(cluster_gene_df$cluster) & nzchar(cluster_gene_df$gene), , drop = FALSE]

    clusters <- sort(unique(cluster_gene_df$cluster))
    files <- gmt_files(database, gmt_base_dir)
    term_sets <- lapply(files, read_term2gene)

    rows <- list()
    for (cluster_id in clusters) {
      gene_list <- unique(cluster_gene_df$gene[cluster_gene_df$cluster == cluster_id])
      if (length(gene_list) < 3) {
        next
      }
      for (category in names(term_sets)) {
        result <- enrich_one_category(cluster_id, gene_list, category, term_sets[[category]])
        if (nrow(result) > 0) {
          rows[[length(rows) + 1]] <- result
        }
      }
    }

    result_df <- if (length(rows) > 0) do.call(rbind, rows) else empty_result()
    result_df <- result_df[, RESULT_COLUMNS, drop = FALSE]
    arrow::write_parquet(result_df, output_path)

    emit_json(list(
      clusters = as.list(as.integer(clusters)),
      selected_cluster = if (length(clusters) > 0) as.integer(clusters[[1]]) else 0L,
      n_terms = nrow(result_df)
    ))
  },
  error = function(e) {
    emit_json(list(error = conditionMessage(e)))
    quit(save = "no", status = 1)
  }
)
