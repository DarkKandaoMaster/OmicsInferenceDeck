suppressPackageStartupMessages({
  library(AnnotationDbi)
  library(org.Hs.eg.db)
})

args <- commandArgs(trailingOnly = TRUE)

get_arg <- function(name, default = NULL) {
  flag <- paste0("--", name)
  idx <- match(flag, args)
  if (is.na(idx)) {
    return(default)
  }
  if (idx == length(args)) {
    stop("Missing value for ", flag, call. = FALSE)
  }
  args[[idx + 1]]
}

input_file <- get_arg("input", "rna_entrez.fea")
output_file <- get_arg("output", "rna_symbol.fea")

required_packages <- c("AnnotationDbi", "org.Hs.eg.db")
missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing_packages) > 0) {
  stop(
    paste0(
      "Missing R package(s): ",
      paste(missing_packages, collapse = ", "),
      "\nInstall with:\n",
      "if (!requireNamespace('BiocManager', quietly = TRUE)) install.packages('BiocManager')\n",
      "BiocManager::install('org.Hs.eg.db')"
    ),
    call. = FALSE
  )
}

dat <- read.csv(input_file, check.names = FALSE, stringsAsFactors = FALSE)
if (ncol(dat) == 0) {
  stop("Input file has no columns: ", input_file, call. = FALSE)
}

entrez_ids <- as.character(dat[[1]])
symbol_map <- AnnotationDbi::mapIds(
  org.Hs.eg.db,
  keys = unique(entrez_ids),
  keytype = "ENTREZID",
  column = "SYMBOL",
  multiVals = "first"
)

symbols <- unname(symbol_map[entrez_ids])
unmapped <- is.na(symbols) | symbols == ""
symbols[unmapped] <- entrez_ids[unmapped]

dat[[1]] <- make.unique(symbols, sep = "_dup")
write.csv(dat, output_file, row.names = FALSE, quote = FALSE)

message("Mapped ", sum(!unmapped), " rows to Gene Symbol; kept ", sum(unmapped), " unmapped Entrez IDs.")
