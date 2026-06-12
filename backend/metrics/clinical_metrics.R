# Calculate clinical clustering metrics from a merged clinical/cluster parquet.
# Usage: Rscript clinical_metrics.R <merged_clinical_cluster.parquet>

suppressPackageStartupMessages({
  library(arrow)
  library(survival)
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
    return("null")
  }

  if (is.data.frame(value)) {
    rows <- lapply(seq_len(nrow(value)), function(index) as.list(value[index, , drop = FALSE]))
    return(to_json(rows))
  }

  if (is.list(value)) {
    value_names <- names(value)
    if (is.null(value_names)) {
      items <- vapply(value, to_json, character(1))
      return(paste0("[", paste(items, collapse = ","), "]"))
    }

    pairs <- vapply(
      seq_along(value),
      function(index) paste0(json_escape(value_names[[index]]), ":", to_json(value[[index]])),
      character(1)
    )
    return(paste0("{", paste(pairs, collapse = ","), "}"))
  }

  if (length(value) != 1) {
    return(to_json(as.list(value)))
  }

  if (inherits(value, "factor") || inherits(value, "Date") || inherits(value, "POSIXt")) {
    value <- as.character(value)
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

emit_error <- function(message) {
  emit_json(list(error = message))
}

finite_or_na <- function(value) {
  value <- suppressWarnings(as.numeric(value[1]))
  if (is.na(value) || !is.finite(value)) {
    return(NA_real_)
  }
  value
}

clean_text <- function(values) {
  text <- as.character(values)
  text[is.na(text) | trimws(text) == ""] <- NA_character_
  text
}

is_integer_like <- function(values) {
  values <- values[!is.na(values)]
  if (length(values) == 0) {
    return(FALSE)
  }
  all(abs(values - round(values)) < 1e-8)
}

compute_lrt <- function(df) {
  survival_df <- df[, c("OS.time", "OS", "Cluster"), drop = FALSE]
  survival_df[["OS.time"]] <- suppressWarnings(as.numeric(clean_text(survival_df[["OS.time"]])))
  survival_df[["OS"]] <- suppressWarnings(as.numeric(clean_text(survival_df[["OS"]])))
  survival_df[["Cluster"]] <- as.factor(clean_text(survival_df[["Cluster"]]))
  survival_df <- survival_df[complete.cases(survival_df), , drop = FALSE]
  survival_df[["Cluster"]] <- droplevels(survival_df[["Cluster"]])

  n_samples <- nrow(survival_df)
  n_clusters <- nlevels(survival_df[["Cluster"]])

  if (n_samples == 0) {
    return(list(
      p_value = NA_real_,
      n_samples = 0,
      n_clusters = 0,
      error = "No valid OS/OS.time rows are available."
    ))
  }

  if (n_clusters < 2) {
    return(list(
      p_value = NA_real_,
      n_samples = n_samples,
      n_clusters = n_clusters,
      error = "At least two clusters are required for the log-rank test."
    ))
  }

  result <- tryCatch(
    {
      fit <- survival::survdiff(survival::Surv(OS.time, OS) ~ Cluster, data = survival_df)
      p_value <- stats::pchisq(fit$chisq, df = max(length(fit$n) - 1, 1), lower.tail = FALSE)
      list(
        p_value = finite_or_na(p_value),
        n_samples = n_samples,
        n_clusters = n_clusters,
        error = NA_character_
      )
    },
    error = function(error) {
      list(
        p_value = NA_real_,
        n_samples = n_samples,
        n_clusters = n_clusters,
        error = conditionMessage(error)
      )
    }
  )

  result
}

prepare_ecp_data <- function(df) {
  excluded <- c("sample_name", "Cluster", "OS", "OS.time")
  candidate_vars <- setdiff(names(df), excluded)
  analysis_df <- df[, "Cluster", drop = FALSE]
  analysis_df[["Cluster"]] <- as.factor(clean_text(analysis_df[["Cluster"]]))

  discrete_vars <- c()
  numerical_vars <- c()
  prepared_vars <- c()

  for (variable in candidate_vars) {
    raw_values <- df[[variable]]
    cluster_values <- analysis_df[["Cluster"]]
    value_text <- clean_text(raw_values)
    valid_mask <- !is.na(value_text) & !is.na(cluster_values)

    if (sum(valid_mask) < 2) {
      next
    }

    valid_clusters <- droplevels(cluster_values[valid_mask])
    if (nlevels(valid_clusters) < 2) {
      next
    }

    parsed_values <- suppressWarnings(as.numeric(value_text))
    is_numeric_parameter <- all(!is.na(parsed_values[valid_mask]))

    if (is_numeric_parameter) {
      unique_values <- unique(parsed_values[valid_mask])
      unique_values <- unique_values[!is.na(unique_values)]
      if (length(unique_values) < 2) {
        next
      }

      if (length(unique_values) <= 10 && is_integer_like(unique_values)) {
        analysis_df[[variable]] <- as.factor(value_text)
        discrete_vars <- c(discrete_vars, variable)
      } else {
        analysis_df[[variable]] <- parsed_values
        numerical_vars <- c(numerical_vars, variable)
      }
    } else {
      unique_values <- unique(value_text[valid_mask])
      unique_values <- unique_values[!is.na(unique_values)]
      if (length(unique_values) < 2) {
        next
      }

      analysis_df[[variable]] <- as.factor(value_text)
      discrete_vars <- c(discrete_vars, variable)
    }

    prepared_vars <- c(prepared_vars, variable)
  }

  list(
    data = analysis_df[, c("Cluster", prepared_vars), drop = FALSE],
    discrete_vars = discrete_vars,
    numerical_vars = numerical_vars,
    prepared_vars = prepared_vars,
    candidate_count = length(candidate_vars)
  )
}

# Permutation empirical p-value for a single clinical parameter against the
# cluster labels. Mirrors the senior reference implementation
# (Subtype-MVCC analysis.R: get.empirical.clinical):
#   - discrete parameter -> chisq.test on the contingency table
#   - numeric parameter  -> kruskal.test of values against cluster groups
# Permutations shuffle the cluster labels in batches; after each batch a
# binom.test confidence interval decides whether the empirical p-value is
# resolved with respect to `alpha`. Returns the binom.test estimate, or NA
# when the test cannot be evaluated (degenerate contingency table, etc.).
empirical_clinical_pvalue <- function(cluster_labels, clinical_values, is_discrete,
                                      alpha = 0.05, batch = 1000, max_iter = 1e5,
                                      seed = 42) {
  set.seed(seed)
  cluster <- as.factor(cluster_labels)
  valid <- !is.na(clinical_values) & !is.na(cluster)
  clinical_clean <- clinical_values[valid]
  cluster_clean <- droplevels(cluster[valid])
  if (is.factor(clinical_clean)) {
    clinical_clean <- droplevels(clinical_clean)
  }

  compute_p <- function(cluster_vec) {
    tryCatch(
      {
        if (is_discrete) {
          contingency <- table(cluster_vec, clinical_clean)
          if (nrow(contingency) < 2 || ncol(contingency) < 2) {
            return(NA_real_)
          }
          suppressWarnings(stats::chisq.test(contingency)$p.value)
        } else {
          stats::kruskal.test(as.numeric(clinical_clean), cluster_vec)$p.value
        }
      },
      error = function(error) NA_real_
    )
  }

  orig_p <- compute_p(cluster_clean)
  if (is.na(orig_p) || !is.finite(orig_p)) {
    return(NA_real_)
  }

  total_iters <- 0L
  total_extreme <- 0L
  estimate <- NA_real_
  repeat {
    perm_p <- vapply(seq_len(batch), function(i) compute_p(sample(cluster_clean)), numeric(1))
    perm_p <- perm_p[!is.na(perm_p)]
    if (length(perm_p) > 0) {
      total_iters <- total_iters + length(perm_p)
      total_extreme <- total_extreme + sum(perm_p <= orig_p)
    }
    if (total_iters == 0L) {
      return(NA_real_)
    }

    bt <- stats::binom.test(total_extreme, total_iters)
    estimate <- as.numeric(bt$estimate)
    ci_low <- bt$conf.int[1]
    ci_high <- bt$conf.int[2]

    if (!(ci_low < alpha && ci_high > alpha) || total_iters > max_iter) {
      break
    }
  }

  estimate
}

compute_ecp <- function(df, alpha = 0.05) {
  method_name <- "permutation empirical p-value + Bonferroni (Subtype-MLMOSC)"

  prepared <- prepare_ecp_data(df)
  prepared_vars <- prepared$prepared_vars
  n_total <- nrow(df)

  if (length(prepared_vars) == 0) {
    return(list(
      method = method_name,
      total_parameters = 0,
      significant_count = 0,
      significance_level = alpha,
      min_p_value = NA_real_,
      skipped_parameters = prepared$candidate_count,
      results = list()
    ))
  }

  analysis_df <- prepared$data
  cluster_labels <- analysis_df[["Cluster"]]

  # Compute the permutation empirical p-value for every prepared parameter,
  # applying the senior "skip when more than half the values are missing" rule
  # and dropping parameters whose test cannot be evaluated.
  raw_results <- list()
  for (variable in prepared_vars) {
    is_discrete <- variable %in% prepared$discrete_vars
    clinical_values <- analysis_df[[variable]]

    valid_count <- sum(!is.na(clinical_values) & !is.na(cluster_labels))
    if (valid_count < (n_total / 2)) {
      next
    }

    p_value <- empirical_clinical_pvalue(cluster_labels, clinical_values, is_discrete)
    if (is.na(p_value)) {
      next
    }

    raw_results[[length(raw_results) + 1]] <- list(
      variable = variable,
      is_discrete = is_discrete,
      p_value = p_value
    )
  }

  n_tested <- length(raw_results)

  # Bonferroni: a parameter is enriched when p * (number of tests) < alpha,
  # which is equivalent to the senior sum(p * length(enrichment.value) < 0.05).
  results <- lapply(raw_results, function(item) {
    adjusted <- item$p_value * n_tested
    list(
      variable = item$variable,
      label = item$variable,
      parameter_type = if (item$is_discrete) "discrete" else "numerical",
      test = if (item$is_discrete) "chisq.test (permutation)" else "kruskal.test (permutation)",
      p_value = item$p_value,
      significant = !is.na(adjusted) && adjusted < alpha
    )
  })

  if (length(results) > 0) {
    order_index <- order(vapply(results, function(item) {
      if (is.na(item$p_value)) Inf else item$p_value
    }, numeric(1)))
    results <- results[order_index]
  }

  p_values <- vapply(results, function(item) item$p_value, numeric(1))
  finite_p_values <- p_values[!is.na(p_values) & is.finite(p_values)]
  min_p_value <- if (length(finite_p_values) > 0) min(finite_p_values) else NA_real_

  list(
    method = method_name,
    total_parameters = n_tested,
    significant_count = sum(vapply(results, function(item) isTRUE(item$significant), logical(1))),
    significance_level = alpha,
    min_p_value = min_p_value,
    skipped_parameters = max(prepared$candidate_count - n_tested, 0),
    results = results
  )
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  emit_error("Usage: Rscript clinical_metrics.R <merged_clinical_cluster.parquet>")
  quit(save = "no", status = 1)
}

tryCatch(
  {
    df <- as.data.frame(suppressWarnings(suppressMessages(
      arrow::read_parquet(args[1], as_data_frame = TRUE)
    )))

    required_columns <- c("Cluster", "OS", "OS.time")
    missing_columns <- setdiff(required_columns, names(df))
    if (length(missing_columns) > 0) {
      stop(paste0("Required column(s) missing: ", paste(missing_columns, collapse = ", ")))
    }

    ecp <- compute_ecp(df)
    payload <- list(
      lrt = compute_lrt(df),
      ecp = ecp,
      n_samples = nrow(df)
    )
    emit_json(payload)
  },
  error = function(error) {
    emit_error(conditionMessage(error))
    quit(save = "no", status = 1)
  }
)
