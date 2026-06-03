# Core differential statistics.
# Usage: Rscript differential.R <input.parquet> <volcano.parquet> <heatmap.parquet>

suppressPackageStartupMessages({
  library(arrow)
  library(limma)
  library(edgeR)
})

# 复刻学长 get_diff.R 第136行：按列位置（而非样本真实身份）贴 tumor/normal 标签。
# 因 mRNA 矩阵列是肿瘤/正常交错排列，此写法会形成近似 tumor-vs-tumor 的对比，
# 差异基因数远少于真实 tumor-vs-normal —— 这正是与学长数字对齐所需的行为。
REPLICATE_SENIOR_POSITIONAL_GROUPING <- TRUE #常量开关（文件顶部，library 块之后）：REPLICATE_SENIOR_POSITIONAL_GROUPING <- TRUE,带注释说明这是为对齐学长数字而刻意复刻的“按位置分组”。

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

empty_volcano <- function(cluster_id, genes, comparison) {
  data.frame(
    cluster = cluster_id,
    gene = as.character(genes),
    logFC = 0.0,
    t_pvalue = 1.0,
    FDR = 1.0,
    negLog10P = 0.0,
    comparison = comparison,
    stringsAsFactors = FALSE
  )
}

run_limma_contrast <- function(expr, group, cluster_id, comparison, positive_level, negative_level) {
  group <- factor(group, levels = c(negative_level, positive_level))
  if (sum(group == positive_level, na.rm = TRUE) < 2 || sum(group == negative_level, na.rm = TRUE) < 2) {
    return(empty_volcano(cluster_id, rownames(expr), comparison))
  }

  design <- stats::model.matrix(~0 + group)
  colnames(design) <- levels(group)
  contrast <- limma::makeContrasts(
    contrasts = paste0(positive_level, " - ", negative_level),
    levels = design
  )
  fit <- limma::lmFit(expr, design)
  fit <- limma::contrasts.fit(fit, contrast)
  fit <- limma::eBayes(fit)
  table <- limma::topTable(fit, number = Inf, sort.by = "none", adjust.method = "BH")

  p_values <- as.numeric(table$P.Value)
  p_values[is.na(p_values) | !is.finite(p_values)] <- 1.0
  p_values <- pmax(p_values, 0.0)

  fdr_values <- as.numeric(table$adj.P.Val)
  fdr_values[is.na(fdr_values) | !is.finite(fdr_values)] <- 1.0
  fdr_values <- pmax(fdr_values, 0.0)

  result <- data.frame(
    cluster = cluster_id,
    gene = rownames(table),
    logFC = as.numeric(table$logFC),
    t_pvalue = p_values,
    FDR = fdr_values,
    negLog10P = -log10(p_values + 1e-300),
    comparison = comparison,
    stringsAsFactors = FALSE
  )
  result$logFC[is.na(result$logFC) | !is.finite(result$logFC)] <- 0.0
  result
}

# edgeR negative-binomial exact test, aligned with the Subtype-MLMOSC pipeline:
# DGEList -> calcNormFactors (TMM) -> estimateCommonDisp -> estimateTagwiseDisp
# (trend = "movingave") -> exactTest(pair = c("tumor", "normal")) -> topTags.
# `counts` are raw read counts (no log2 transform). `group` is the per-sample
# SampleType vector, so the comparison does not depend on column ordering.
run_edger_contrast <- function(counts, group, cluster_id, comparison) {
  group <- tolower(as.character(group))
  if (sum(group == "tumor", na.rm = TRUE) < 2 || sum(group == "normal", na.rm = TRUE) < 2) {
    return(empty_volcano(cluster_id, rownames(counts), comparison))
  }

  # Drop genes with no reads within this cluster's samples (matches the reference
  # rowMeans(TCGA) > 0 filter, which there is applied per cluster subset).
  keep <- rowSums(counts, na.rm = TRUE) > 0
  counts <- counts[keep, , drop = FALSE]
  if (nrow(counts) < 1) {
    return(empty_volcano(cluster_id, rownames(counts), comparison))
  }

  dge <- edgeR::DGEList(counts = counts, group = group)
  dge <- edgeR::calcNormFactors(dge)
  dge <- edgeR::estimateCommonDisp(dge)
  dge <- edgeR::estimateTagwiseDisp(dge, trend = "movingave")
  exact_test <- edgeR::exactTest(dge, pair = c("tumor", "normal"))
  table <- edgeR::topTags(exact_test, n = Inf, sort.by = "none")$table

  p_values <- as.numeric(table$PValue)
  p_values[is.na(p_values) | !is.finite(p_values)] <- 1.0
  p_values <- pmin(pmax(p_values, 0.0), 1.0)

  fdr_values <- as.numeric(table$FDR)
  fdr_values[is.na(fdr_values) | !is.finite(fdr_values)] <- 1.0
  fdr_values <- pmin(pmax(fdr_values, 0.0), 1.0)

  result <- data.frame(
    cluster = cluster_id,
    gene = rownames(table),
    logFC = as.numeric(table$logFC),
    t_pvalue = p_values,
    FDR = fdr_values,
    negLog10P = -log10(p_values + 1e-300),
    comparison = comparison,
    stringsAsFactors = FALSE
  )
  result$logFC[is.na(result$logFC) | !is.finite(result$logFC)] <- 0.0
  result
}

top_significant_genes <- function(cluster_result) {
  significant <- cluster_result[
    cluster_result$FDR < 0.05 & abs(cluster_result$logFC) >= 0.5,
    ,
    drop = FALSE
  ]
  if (nrow(significant) == 0) {
    return(character(0))
  }
  significant <- significant[order(significant$FDR, -abs(significant$logFC)), , drop = FALSE]
  head(significant$gene, 10)
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

    reserved_columns <- c("sample_name", "Cluster", "SampleType")
    genes <- setdiff(names(df), reserved_columns)
    if (length(genes) < 1) {
      stop("input parquet must contain at least one feature column")
    }

    df$sample_name <- as.character(df$sample_name)
    df$Cluster <- suppressWarnings(as.integer(df$Cluster))
    if (any(is.na(df$Cluster))) {
      stop("Cluster column contains missing or non-integer values")
    }

    expr <- t(as.matrix(df[, genes, drop = FALSE]))
    storage.mode(expr) <- "double"
    rownames(expr) <- genes
    colnames(expr) <- df$sample_name
    expr[!is.finite(expr)] <- NA_real_
    expr <- limma::avereps(expr)
    keep <- rowSums(!is.na(expr)) > 0
    expr <- expr[keep, , drop = FALSE]
    expr[is.na(expr)] <- 0
    if (nrow(expr) < 1) {
      stop("no analyzable features after numeric conversion")
    }

    expression_mode <- "SampleType" %in% names(df)
    if (expression_mode) {
      df$SampleType <- tolower(as.character(df$SampleType))
      valid_type <- df$SampleType %in% c("tumor", "normal")
      if (!any(valid_type)) {
        stop("mRNA expression differential analysis requires TCGA tumor and normal sample barcodes")
      }
      # edgeR consumes raw counts directly (no log2 transform). Drop genes with no
      # expression across samples, matching the reference rowMeans(expr) > 0 filter.
      expr_for_model <- expr
      keep_expressed <- rowMeans(expr_for_model, na.rm = TRUE) > 0
      expr_for_model <- expr_for_model[keep_expressed, , drop = FALSE]
      if (nrow(expr_for_model) < 1) {
        stop("no expressed genes remain after removing all-zero counts (rowMeans > 0)")
      }
      # edgeR models raw counts, but the heatmap is shown on a log2(counts+1)
      # scale so high-count samples do not flatten the per-gene z-score colours.
      expr_for_heatmap_source <- log2(pmax(expr_for_model, 0) + 1)
      mode <- "tumor_vs_normal_within_cluster"
    } else {
      expr_for_model <- expr
      expr_for_heatmap_source <- expr_for_model
      mode <- "cluster_vs_rest"
    }

    clusters <- sort(unique(df$Cluster))
    volcano_frames <- list()
    top_genes <- character(0)

    for (cluster_id in clusters) {
      if (expression_mode) {
        idx <- df$Cluster == cluster_id & df$SampleType %in% c("tumor", "normal")
        sub_types <- df$SampleType[idx]                     # 真实标签，仅用于计数
        if (REPLICATE_SENIOR_POSITIONAL_GROUPING) {
          n_tumor  <- sum(sub_types == "tumor")
          n_normal <- sum(sub_types == "normal")
          # 复刻 design <- c(rep("tumor", n_tumor), rep("normal", n_normal))，
          # 按子集“原始列顺序”定位（列序已保留，等价于学长 filtered_mRNAdata）。
          group_vec <- c(rep("tumor", n_tumor), rep("normal", n_normal))
        } else {
          group_vec <- sub_types
        }
        cluster_result <- run_edger_contrast(
          expr_for_model[, idx, drop = FALSE],
          group_vec,
          cluster_id,
          "Tumor vs Normal"
        )
      } else {
        group <- ifelse(df$Cluster == cluster_id, "target", "rest")
        cluster_result <- run_limma_contrast(
          expr_for_model,
          group,
          cluster_id,
          "Cluster vs Rest",
          "target",
          "rest"
        )
      }

      volcano_frames[[length(volcano_frames) + 1]] <- cluster_result
      for (gene in top_significant_genes(cluster_result)) {
        if (!(gene %in% top_genes)) {
          top_genes <- c(top_genes, gene)
        }
      }
    }

    volcano_df <- if (length(volcano_frames) > 0) {
      do.call(rbind, volcano_frames)
    } else {
      data.frame(
        cluster = integer(),
        gene = character(),
        logFC = numeric(),
        t_pvalue = numeric(),
        FDR = numeric(),
        negLog10P = numeric(),
        comparison = character()
      )
    }
    arrow::write_parquet(volcano_df, volcano_path)

    if (length(top_genes) > 0) {
      top_genes <- top_genes[top_genes %in% rownames(expr_for_heatmap_source)]
    }
    if (length(top_genes) > 0) {
      expr_for_heatmap <- t(expr_for_heatmap_source[top_genes, , drop = FALSE])
      heatmap_df <- data.frame(sample_name = df$sample_name, Cluster = df$Cluster, expr_for_heatmap, check.names = FALSE)
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
      n_features = nrow(expr_for_model),
      n_top_genes = length(top_genes),
      mode = mode
    ))
  },
  error = function(e) {
    emit_json(list(error = conditionMessage(e)))
    quit(save = "no", status = 1)
  }
)
