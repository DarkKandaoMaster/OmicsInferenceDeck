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
    # digits = 17：用最多 17 位有效数字输出 double，基本能保证 R/Python 之间往返解析时不丢关键精度。
    # scientific = FALSE：尽量不用科学计数法，输出普通小数形式。
    # trim = TRUE：去掉多余空格，避免 JSON 里出现不必要的格式字符。
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

emit_success <- function(sample_names, labels, embeddings, estimated_k) {
  cat(
    paste0(
      "{\"status\":\"success\"",
      ",\"sample_names\":", json_string_vector(sample_names),
      ",\"labels\":", json_number_vector(labels),
      ",\"embeddings\":", json_numeric_matrix(embeddings),
      ",\"n_samples\":", json_value(length(sample_names)),
      ",\"n_features\":", json_value(ncol(embeddings)),
      ",\"estimated_k\":", json_value(estimated_k),
      "}\n"
    )
  )
}

emit_error <- function(message) {
  cat(paste0("{\"error\":", json_escape(message), "}\n"))
}

parse_k <- function(value) {
  if (length(value) == 0 || value == "" || toupper(value) == "NULL") {
    return(NULL)
  }
  parsed <- suppressWarnings(as.integer(value))
  if (is.na(parsed) || parsed <= 0) {
    return(NULL)
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
    mat
  })

  if (any(vapply(matrices, function(mat) any(!is.finite(mat)), logical(1)))) {
    stop("Saved omics data contains missing or non-numeric values. Please check upload alignment and input cleaning.")
  }

  list(sample_names = sample_names, matrices = matrices)
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  emit_error("Usage: Rscript mosd.R <omics_parquet> <n_clusters> [random_seed]")
  quit(save = "no", status = 1)
}

tryCatch(
  {
    input_path <- args[1]
    k <- parse_k(args[2])
    seed_arg <- if (length(args) >= 3) args[3] else ""

    if (!file.exists(input_path)) {
      stop(paste("Input parquet not found:", input_path))
    }
    if (!requireNamespace("MOSD", quietly = TRUE)) {
      stop('R package MOSD is not installed. Install it with devtools::install_github("DXCODEE/MOSD").')
    }
    if (seed_arg != "") {
      seed <- suppressWarnings(as.integer(seed_arg))
      if (!is.na(seed)) {
        set.seed(seed)
      }
    }

    loaded <- frame_matrices_from_parquet(input_path)
    mosd_result <- MOSD::MOSD(loaded$matrices, k)

    labels <- suppressWarnings(as.integer(mosd_result$clu))
    if (length(labels) != length(loaded$sample_names) || any(is.na(labels))) {
      stop("MOSD returned invalid clustering labels.")
    }

    embeddings <- as.matrix(mosd_result$S)
    storage.mode(embeddings) <- "double"
    if (nrow(embeddings) != length(loaded$sample_names)) {
      stop("MOSD returned an integrated matrix with an unexpected number of rows.")
    }
    if (any(!is.finite(embeddings))) {
      stop("MOSD returned missing or non-finite embedding values.")
    }

    emit_success(loaded$sample_names, labels, embeddings, mosd_result$es)
  },
  error = function(e) {
    emit_error(conditionMessage(e))
    quit(save = "no", status = 1)
  }
)
