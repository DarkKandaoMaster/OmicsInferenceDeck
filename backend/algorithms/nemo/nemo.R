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

json_numeric_matrix <- function(mat) {
  rows <- vapply(
    seq_len(nrow(mat)),
    function(i) json_number_vector(mat[i, ]),
    character(1)
  )
  paste0("[", paste(rows, collapse = ","), "]")
}

emit_success <- function(sample_names, labels, embeddings, n_neighbors) {
  cat(
    paste0(
      "{\"status\":\"success\"",
      ",\"sample_names\":", json_string_vector(sample_names),
      ",\"labels\":", json_number_vector(labels),
      ",\"embeddings\":", json_numeric_matrix(embeddings),
      ",\"n_samples\":", json_value(length(sample_names)),
      ",\"n_features\":", json_value(ncol(embeddings)),
      ",\"n_neighbors\":", json_value(n_neighbors),
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

frame_matrices_from_parquet <- function(input_path) {
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
    scaled <- scale(mat)
    storage.mode(scaled) <- "double"
    # NEMO expects each omic matrix as features x samples.
    transposed <- t(scaled)
    colnames(transposed) <- sample_names
    transposed
  })

  if (any(vapply(matrices, function(mat) any(!is.finite(mat)), logical(1)))) {
    stop("Saved omics data contains missing or non-numeric values. Please check upload alignment and input cleaning.")
  }

  list(sample_names = sample_names, matrices = matrices)
}

embedding_from_affinity <- function(affinity, n_components) {
  affinity <- as.matrix(affinity)
  affinity <- (affinity + t(affinity)) / 2
  diag(affinity) <- 0

  degree <- rowSums(affinity)
  degree[degree <= 0 | !is.finite(degree)] <- .Machine$double.eps
  normalized <- diag(1 / sqrt(degree), nrow = length(degree)) %*% affinity %*% diag(1 / sqrt(degree), nrow = length(degree))
  normalized <- (normalized + t(normalized)) / 2

  eig <- eigen(normalized, symmetric = TRUE)
  order_idx <- order(eig$values, decreasing = TRUE)
  keep <- order_idx[seq_len(min(n_components, length(order_idx)))]
  embeddings <- as.matrix(eig$vectors[, keep, drop = FALSE])
  storage.mode(embeddings) <- "double"
  embeddings
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  emit_error("Usage: Rscript nemo.R <omics_parquet> <n_clusters> <n_neighbors> [random_seed]")
  quit(save = "no", status = 1)
}

tryCatch(
  {
    if (!requireNamespace("NEMO", quietly = TRUE)) {
      stop("R package NEMO is not installed. Install it with: devtools::install_github(\"Shamir-Lab/NEMO/NEMO\")")
    }
    if (!requireNamespace("SNFtool", quietly = TRUE)) {
      stop("R package SNFtool is not installed. NEMO requires it; install it with: install.packages(\"SNFtool\")")
    }
    suppressPackageStartupMessages({
      library(SNFtool)
      library(NEMO)
    })

    input_path <- args[1]
    n_clusters <- parse_positive_int(args[2], 3)
    n_neighbors <- parse_positive_int(args[3], 0)
    seed_arg <- if (length(args) >= 4) args[4] else ""

    if (!file.exists(input_path)) {
      stop(paste("Input parquet not found:", input_path))
    }
    if (seed_arg != "") {
      seed <- suppressWarnings(as.integer(seed_arg))
      if (!is.na(seed)) {
        set.seed(seed)
      }
    }

    loaded <- frame_matrices_from_parquet(input_path)
    n_samples <- length(loaded$sample_names)
    if (n_samples < 3) {
      stop("NEMO requires at least three samples.")
    }
    if (n_clusters < 2) {
      stop("NEMO n_clusters must be at least 2.")
    }
    if (n_clusters > n_samples) {
      stop("NEMO n_clusters cannot be greater than the number of samples.")
    }

    if (n_neighbors <= 0) {
      n_neighbors <- max(2, floor(n_samples / 6))
    }
    n_neighbors <- min(max(2, n_neighbors), n_samples - 1)

    affinity <- NEMO::nemo.affinity.graph(loaded$matrices, k = n_neighbors)
    affinity <- as.matrix(affinity)
    storage.mode(affinity) <- "double"
    affinity <- (affinity + t(affinity)) / 2

    if (is.null(colnames(affinity))) {
      colnames(affinity) <- loaded$sample_names
    }
    affinity_samples <- as.character(colnames(affinity))
    sample_order <- match(loaded$sample_names, affinity_samples)
    if (any(is.na(sample_order))) {
      stop("NEMO affinity graph did not contain all uploaded sample names.")
    }
    affinity <- affinity[sample_order, sample_order, drop = FALSE]

    if (any(!is.finite(affinity))) {
      stop("NEMO returned missing or non-finite affinity values.")
    }

    labels <- suppressWarnings(as.integer(SNFtool::spectralClustering(affinity, K = n_clusters)))
    if (length(labels) != n_samples || any(is.na(labels))) {
      stop("NEMO spectral clustering returned invalid labels.")
    }

    n_components <- min(10, n_samples - 1)
    embeddings <- embedding_from_affinity(affinity, n_components)
    if (nrow(embeddings) != n_samples || any(!is.finite(embeddings))) {
      stop("NEMO returned invalid spectral embeddings.")
    }

    emit_success(loaded$sample_names, labels, embeddings, n_neighbors)
  },
  error = function(e) {
    emit_error(conditionMessage(e))
    quit(save = "no", status = 1)
  }
)
