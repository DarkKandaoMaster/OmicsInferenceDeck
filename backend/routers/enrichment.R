# Core GO/KEGG enrichment statistics, aligned with the Subtype-MLMOSC pipeline:
# enrichGO / enrichKEGG against org.Hs.eg.db (ENTREZID), not local GMT files.
# Usage: Rscript enrichment.R <database> <input.parquet> <output.parquet> <gmt_base_dir> [genes|volcano]
# NOTE: <gmt_base_dir> is retained for call-signature compatibility but ignored;
# enrichGO/enrichKEGG use org.Hs.eg.db and the online KEGG service instead.

suppressPackageStartupMessages({
  library(arrow)
  library(clusterProfiler)
  library(org.Hs.eg.db)
  library(AnnotationDbi)
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

ratio_numerator <- function(value) {
  parts <- strsplit(as.character(value), "/", fixed = TRUE)[[1]]
  if (length(parts) != 2) {
    return(NA_real_)
  }
  suppressWarnings(as.numeric(parts[[1]]))
}

# Shape an enrichGO/enrichKEGG result frame into the stable parquet schema.
# Significance filtering is already applied by the enrichment engine cutoffs
# (enrichGO pvalueCutoff = 0.1; enrichKEGG p/q cutoff = 0.05); here we only order
# by p-value and optionally keep the top `top_n` rows (NULL keeps all of them).
format_clusterprofiler_result <- function(cluster_id, category, result_df, top_n = NULL) {
  if (is.null(result_df) || nrow(result_df) == 0) {
    return(empty_result())
  }

  result_df <- result_df[order(result_df$pvalue), , drop = FALSE]
  if (!is.null(top_n)) {
    result_df <- head(result_df, top_n)
  }
  if (nrow(result_df) == 0) {
    return(empty_result())
  }

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

# Map gene SYMBOLs to ENTREZIDs via org.Hs.eg.db (bitr drops unmapped symbols).
map_symbols_to_entrez <- function(gene_symbols) {
  gene_symbols <- unique(as.character(gene_symbols))
  if (length(gene_symbols) < 1) {
    return(character(0))
  }
  mapped <- tryCatch(
    suppressWarnings(suppressMessages(
      clusterProfiler::bitr(
        gene_symbols,
        fromType = "SYMBOL",
        toType = "ENTREZID",
        OrgDb = org.Hs.eg.db
      )
    )),
    error = function(e) NULL
  )
  if (is.null(mapped) || nrow(mapped) == 0) {
    return(character(0))
  }
  unique(as.character(mapped$ENTREZID))
}

# GO enrichment for one ontology (BP/CC/MF), top 5 terms per category.
enrich_go_category <- function(cluster_id, entrez_ids, ont) {
  if (length(entrez_ids) < 3) {
    return(empty_result())
  }
  ego <- tryCatch(
    clusterProfiler::enrichGO(
      gene = entrez_ids,
      OrgDb = org.Hs.eg.db,
      keyType = "ENTREZID",
      ont = ont,
      pAdjustMethod = "BH",
      minGSSize = 1,
      pvalueCutoff = 0.1,
      readable = TRUE
    ),
    error = function(e) NULL
  )
  format_clusterprofiler_result(cluster_id, ont, as.data.frame(ego), top_n = 5)
}

# KEGG enrichment (online, organism = "human"); keep all significant pathways.
enrich_kegg <- function(cluster_id, entrez_ids) {
  if (length(entrez_ids) < 3) {
    return(empty_result())
  }
  kk <- tryCatch(
    clusterProfiler::enrichKEGG(
      gene = entrez_ids,
      keyType = "kegg",
      organism = "human",
      pvalueCutoff = 0.05,
      qvalueCutoff = 0.05
    ),
    error = function(e) NULL
  )
  format_clusterprofiler_result(cluster_id, "KEGG", as.data.frame(kk), top_n = NULL)
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
      required_columns <- c("cluster", "gene", "logFC")
      missing_columns <- setdiff(required_columns, names(input_df))
      if (length(missing_columns) > 0) {
        stop(paste0("volcano parquet missing columns: ", paste(missing_columns, collapse = ", ")))
      }
      input_df$logFC <- suppressWarnings(as.numeric(input_df$logFC))
      if ("FDR" %in% names(input_df)) {
        input_df$significance <- suppressWarnings(as.numeric(input_df$FDR))
      } else if ("t_pvalue" %in% names(input_df)) {
        input_df$significance <- suppressWarnings(as.numeric(input_df$t_pvalue))
      } else {
        stop("volcano parquet must contain FDR or t_pvalue")
      }
      keep <- input_df$significance < 0.05 & abs(input_df$logFC) >= 0.5
      cluster_gene_df <- input_df[keep, c("cluster", "gene", "significance"), drop = FALSE]
      cluster_gene_df <- cluster_gene_df[order(cluster_gene_df$cluster, cluster_gene_df$significance), , drop = FALSE]
      cluster_gene_df <- cluster_gene_df[, c("cluster", "gene"), drop = FALSE]
    } else {
      cluster_gene_df <- input_df
    }

    if (!("cluster" %in% names(cluster_gene_df)) || !("gene" %in% names(cluster_gene_df))) {
      stop("input parquet must contain cluster and gene columns")
    }

    cluster_gene_df$cluster <- suppressWarnings(as.integer(cluster_gene_df$cluster))
    cluster_gene_df$gene <- as.character(cluster_gene_df$gene)
    cluster_gene_df <- cluster_gene_df[!is.na(cluster_gene_df$cluster) & nzchar(cluster_gene_df$gene), , drop = FALSE]

    if (!(database %in% c("GO", "KEGG"))) {
      stop("database must be GO or KEGG")
    }

    clusters <- sort(unique(cluster_gene_df$cluster))

    rows <- list()
    for (cluster_id in clusters) {
      gene_list <- unique(cluster_gene_df$gene[cluster_gene_df$cluster == cluster_id])
      if (length(gene_list) < 3) {
        next
      }
      entrez_ids <- map_symbols_to_entrez(gene_list)
      if (length(entrez_ids) < 3) {
        next
      }
      if (database == "GO") {
        for (ont in c("BP", "CC", "MF")) {
          result <- enrich_go_category(cluster_id, entrez_ids, ont)
          if (nrow(result) > 0) {
            rows[[length(rows) + 1]] <- result
          }
        }
      } else {
        result <- enrich_kegg(cluster_id, entrez_ids)
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
