# Calculate clinical clustering metrics from a merged clinical/cluster parquet.
# Usage: Rscript clinical_metrics.R <merged_clinical_cluster.parquet>

suppressPackageStartupMessages({
  library(arrow)
  library(survival)
  library(gtsummary)
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

p_value_or_na <- function(value) {
  if (is.null(value) || length(value) == 0) {
    return(NA_real_)
  }

  if (is.numeric(value) || is.integer(value)) {
    return(finite_or_na(value))
  }

  text <- as.character(value[1])
  if (is.na(text) || trimws(text) == "") {
    return(NA_real_)
  }

  text <- trimws(text)
  text <- sub("^<\\s*", "", text)
  text <- sub("^<=\\s*", "", text)
  text <- gsub(",", "", text, fixed = TRUE)
  finite_or_na(text)
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

get_gtsummary_table_body <- function(summary_table) {
  table_body <- tryCatch(summary_table[["table_body"]], error = function(error) NULL)
  if (is.null(table_body)) {
    table_body <- tryCatch(summary_table$table_body, error = function(error) NULL)
  }
  if (is.null(table_body)) {
    return(data.frame())
  }
  as.data.frame(table_body)
}

manual_ecp_p_value <- function(data, variable, parameter_type) {
  variable_df <- data[, c("Cluster", variable), drop = FALSE]
  variable_df[["Cluster"]] <- droplevels(as.factor(variable_df[["Cluster"]]))
  variable_df <- variable_df[complete.cases(variable_df), , drop = FALSE]

  if (nrow(variable_df) < 2 || nlevels(variable_df[["Cluster"]]) < 2) {
    return(list(p_value = NA_real_, test = NA_character_))
  }

  if (identical(parameter_type, "numerical")) {
    values <- suppressWarnings(as.numeric(variable_df[[variable]]))
    valid_mask <- !is.na(values) & !is.na(variable_df[["Cluster"]])
    values <- values[valid_mask]
    groups <- droplevels(variable_df[["Cluster"]][valid_mask])

    if (length(values) < 2 || nlevels(groups) < 2 || length(unique(values)) < 2) {
      return(list(p_value = NA_real_, test = "kruskal.test"))
    }

    p_value <- tryCatch(
      stats::kruskal.test(values, groups)$p.value,
      error = function(error) NA_real_
    )
    return(list(p_value = finite_or_na(p_value), test = "kruskal.test"))
  }

  groups <- droplevels(as.factor(variable_df[["Cluster"]]))
  values <- droplevels(as.factor(variable_df[[variable]]))
  contingency <- table(values, groups)
  contingency <- contingency[rowSums(contingency) > 0, colSums(contingency) > 0, drop = FALSE]

  if (nrow(contingency) < 2 || ncol(contingency) < 2) {
    return(list(p_value = NA_real_, test = "fisher.test"))
  }

  p_value <- tryCatch(
    stats::fisher.test(contingency)$p.value,
    error = function(error) {
      tryCatch(
        stats::fisher.test(contingency, simulate.p.value = TRUE, B = 10000)$p.value,
        error = function(error) NA_real_
      )
    }
  )
  list(p_value = finite_or_na(p_value), test = "fisher.test")
}

compute_ecp <- function(df, alpha = 0.05) {
  prepared <- prepare_ecp_data(df)
  prepared_vars <- prepared$prepared_vars

  if (length(prepared_vars) == 0) {
    return(list(
      method = "gtsummary::tbl_summary + add_p",
      total_parameters = 0,
      significant_count = 0,
      significance_level = alpha,
      min_p_value = NA_real_,
      skipped_parameters = prepared$candidate_count,
      results = list()
    ))
  }

  table <- gtsummary::tbl_summary(
    data = prepared$data,
    by = "Cluster",
    missing = "no"
  )
  table <- tryCatch(
    suppressWarnings(suppressMessages(gtsummary::add_p(table))),
    error = function(error) table
  )
  table_body <- get_gtsummary_table_body(table)
  label_rows <- table_body[table_body$row_type == "label", , drop = FALSE]

  results <- list()
  for (row_index in seq_len(nrow(label_rows))) {
    variable <- as.character(label_rows$variable[[row_index]])
    p_value <- if ("p.value" %in% names(label_rows)) {
      p_value_or_na(label_rows[["p.value"]][[row_index]])
    } else if ("p_value" %in% names(label_rows)) {
      p_value_or_na(label_rows[["p_value"]][[row_index]])
    } else if ("**p-value**" %in% names(label_rows)) {
      p_value_or_na(label_rows[["**p-value**"]][[row_index]])
    } else {
      NA_real_
    }
    parameter_type <- if (variable %in% prepared$discrete_vars) "discrete" else "numerical"
    test_name <- if ("test_name" %in% names(label_rows)) {
      as.character(label_rows$test_name[[row_index]])
    } else if ("test" %in% names(label_rows)) {
      as.character(label_rows$test[[row_index]])
    } else {
      "gtsummary default"
    }
    if (is.na(test_name) || trimws(test_name) == "") {
      test_name <- "gtsummary default"
    }
    label <- if ("label" %in% names(label_rows)) as.character(label_rows$label[[row_index]]) else variable

    if (is.na(p_value)) {
      manual_result <- manual_ecp_p_value(prepared$data, variable, parameter_type)
      p_value <- manual_result$p_value
      if (!is.na(manual_result$test)) {
        test_name <- manual_result$test
      }
    }
 results[[length(results) + 1]] <- list(
      variable = variable,
      label = label,
      parameter_type = parameter_type,
      test = test_name,
      p_value = p_value,
      significant = !is.na(p_value) && p_value < alpha
    )
  }

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
    method = "gtsummary::tbl_summary + add_p",
    total_parameters = length(results),
    significant_count = sum(vapply(results, function(item) isTRUE(item$significant), logical(1))),
    significance_level = alpha,
    min_p_value = min_p_value,
    skipped_parameters = max(prepared$candidate_count - length(results), 0),
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
