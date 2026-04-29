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
  if (is.null(value) || length(value) == 0) {
    return("null")
  }
  if (is.list(value)) {
    value <- unlist(value, recursive = TRUE, use.names = FALSE)
    if (length(value) == 0) {
      return("null")
    }
  }
  if (is.numeric(value) || is.integer(value)) {
    value <- as.numeric(value[1])
    if (is.na(value) || !is.finite(value)) {
      return("null")
    }
    return(format(value, scientific = FALSE, trim = TRUE, digits = 17))
  }
  json_escape(value[1])
}

json_string_vector <- function(values) {
  paste0("[", paste(vapply(values, json_escape, character(1)), collapse = ","), "]")
}

json_number_vector <- function(values) {
  paste0("[", paste(vapply(values, json_value, character(1)), collapse = ","), "]")
}

json_numeric_matrix <- function(mat) {
  rows <- vapply(
    seq_len(nrow(mat)),
    function(i) json_number_vector(mat[i, ]),
    character(1)
  )
  paste0("[", paste(rows, collapse = ","), "]")
}

emit_success <- function(sample_names, labels, embeddings, latent_dim, max_it) {
  cat(
    paste0(
      "{\"status\":\"success\"",
      ",\"sample_names\":", json_string_vector(sample_names),
      ",\"labels\":", json_number_vector(labels),
      ",\"embeddings\":", json_numeric_matrix(embeddings),
      ",\"n_samples\":", json_value(length(sample_names)),
      ",\"n_features\":", json_value(ncol(embeddings)),
      ",\"latent_dim\":", json_value(latent_dim),
      ",\"max_it\":", json_value(max_it),
      "}\n"
    )
  )
}

emit_error <- function(message) {
  cat(paste0("{\"error\":", json_escape(message), "}\n"))
}

parse_positive_int <- function(value, default_value) {
  if (length(value) == 0 || value == "" || toupper(value) == "NULL") {
    return(default_value)
  }
  parsed <- suppressWarnings(as.integer(value))
  if (is.na(parsed) || parsed <= 0) {
    return(default_value)
  }
  parsed
}

select_top_variable_features <- function(mat, max_features, frame_id) {
  if (is.null(max_features) || max_features <= 0 || ncol(mat) <= max_features) {
    return(mat)
  }

  variances <- apply(mat, 2, stats::var)
  variances[!is.finite(variances)] <- -Inf
  keep_idx <- order(variances, decreasing = TRUE)[seq_len(max_features)]
  if (length(keep_idx) == 0 || all(!is.finite(variances[keep_idx]))) {
    stop(paste("No finite variable features remain in", frame_id))
  }
  mat[, keep_idx, drop = FALSE]
}

frame_matrices_from_parquet <- function(input_path, max_features) {
  df <- suppressWarnings(suppressMessages(
    arrow::read_parquet(input_path, as_data_frame = TRUE)
  ))

  if (!("sample_name" %in% names(df))) {
    stop("Saved omics parquet must contain a sample_name column.")
  }

  sample_names <- as.character(df$sample_name)
  storage_cols <- grep("^frame_[0-9]+__col_[0-9]+$", names(df), value = TRUE)
  if (length(storage_cols) == 0) {
    stop("Saved omics parquet does not contain frame_*__col_* feature columns.")
  }

  frame_ids <- unique(sub("^(frame_[0-9]+)__.*$", "\\1", storage_cols))
  matrices <- lapply(frame_ids, function(frame_id) {
    cols <- grep(paste0("^", frame_id, "__col_[0-9]+$"), storage_cols, value = TRUE)
    mat <- as.matrix(df[, cols, drop = FALSE])
    storage.mode(mat) <- "double"
    rownames(mat) <- sample_names
    keep_cols <- apply(mat, 2, function(col) {
      all(is.finite(col)) && stats::sd(col) > 0
    })
    mat <- mat[, keep_cols, drop = FALSE]
    if (ncol(mat) == 0) {
      stop(paste("All features were removed from", frame_id, "because they are constant or invalid."))
    }
    mat <- select_top_variable_features(mat, max_features, frame_id)
    scale(mat)
  })

  if (any(vapply(matrices, function(mat) any(!is.finite(mat)), logical(1)))) {
    stop("Saved omics data contains missing or non-numeric values. Please check upload alignment and input cleaning.")
  }

  list(sample_names = sample_names, matrices = matrices)
}

force_future_sapply_list <- function() {
  ns <- asNamespace("future.apply")
  original <- get("future_sapply", envir = ns)
  wrapper <- function(X, FUN, ..., simplify = TRUE, USE.NAMES = TRUE,
                      future.envir = parent.frame(), future.label = "future_sapply-%d") {
    original(
      X,
      FUN,
      ...,
      simplify = FALSE,
      USE.NAMES = USE.NAMES,
      future.envir = future.envir,
      future.label = future.label
    )
  }
  unlockBinding("future_sapply", ns)
  assign("future_sapply", wrapper, envir = ns)
  lockBinding("future_sapply", ns)
  original
}

restore_future_sapply <- function(original) {
  if (is.null(original)) {
    return(invisible(NULL))
  }
  ns <- asNamespace("future.apply")
  unlockBinding("future_sapply", ns)
  assign("future_sapply", original, envir = ns)
  lockBinding("future_sapply", ns)
  invisible(NULL)
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 5) {
  emit_error("Usage: Rscript pintmf.R <omics_parquet> <n_clusters> <latent_dim> <max_it> [random_seed] [init_flavor] [flavor_mod] [flavor_mod_w] [max_features]")
  quit(save = "no", status = 1)
}

tryCatch(
  {
    if (!requireNamespace("PintMF", quietly = TRUE)) {
      stop("R package PintMF is not installed. Install it with: devtools::install_github(\"mpierrejean/pintmf\")")
    }

    input_path <- args[1]
    n_clusters <- parse_positive_int(args[2], 3)
    latent_dim <- parse_positive_int(args[3], n_clusters)
    max_it <- parse_positive_int(args[4], 20)
    seed_arg <- if (length(args) >= 5) args[5] else ""
    init_flavor <- if (length(args) >= 6 && args[6] != "") args[6] else "snf"
    flavor_mod <- if (length(args) >= 7 && args[7] != "") args[7] else "glmnet"
    flavor_mod_w <- if (length(args) >= 8 && args[8] != "") args[8] else "glmnet"
    max_features <- if (length(args) >= 9) parse_positive_int(args[9], 500) else 500

    if (!file.exists(input_path)) {
      stop(paste("Input parquet not found:", input_path))
    }
    if (seed_arg != "") {
      seed <- suppressWarnings(as.integer(seed_arg))
      if (!is.na(seed)) {
        set.seed(seed)
      }
    }

    loaded <- frame_matrices_from_parquet(input_path, max_features)
    if (length(loaded$matrices) < 2) {
      stop("PIntMF requires at least two omics matrices.")
    }
    if (latent_dim < 2) {
      stop("PIntMF latent_dim must be at least 2.")
    }

    original_future_sapply <- force_future_sapply_list()
    on.exit(restore_future_sapply(original_future_sapply), add = TRUE)

    capture.output(
      {
        pintmf_result <- suppressWarnings(suppressMessages(
          PintMF::SolveInt(
            Y = loaded$matrices,
            p = latent_dim,
            max.it = max_it,
            verbose = FALSE,
            init_flavor = init_flavor,
            flavor_mod = flavor_mod,
            flavor_mod_W = flavor_mod_w
          )
        ))
      },
      type = "output"
    )
    restore_future_sapply(original_future_sapply)
    original_future_sapply <- NULL

    embeddings <- as.matrix(pintmf_result$W)
    storage.mode(embeddings) <- "double"
    if (nrow(embeddings) != length(loaded$sample_names)) {
      stop("PIntMF returned W with an unexpected number of rows.")
    }
    if (any(!is.finite(embeddings))) {
      stop("PIntMF returned missing or non-finite embedding values.")
    }

    labels <- stats::dist(embeddings) |>
      stats::hclust(method = "ward.D2") |>
      stats::cutree(k = n_clusters)
    labels <- suppressWarnings(as.integer(labels))
    if (length(labels) != length(loaded$sample_names) || any(is.na(labels))) {
      stop("PIntMF returned invalid clustering labels.")
    }

    emit_success(loaded$sample_names, labels, embeddings, latent_dim, max_it)
  },
  error = function(e) {
    emit_error(conditionMessage(e))
    quit(save = "no", status = 1)
  }
)
