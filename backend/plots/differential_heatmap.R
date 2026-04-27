suppressPackageStartupMessages({
  library(arrow)
  library(pheatmap)
  library(svglite)
  library(grid)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("Usage: Rscript differential_heatmap.R <heatmap.parquet>")
}

heatmap_path <- args[[1]]
output_format <- if (length(args) >= 2) tolower(args[[2]]) else ""
output_path <- if (length(args) >= 3) args[[3]] else ""
is_download <- output_format %in% c("png", "svg", "pdf") && nzchar(output_path)
FONT_FAMILY <- "serif"

open_plot_device <- function(width, height) {
  if (output_format == "png") {
    grDevices::png(output_path, width = width, height = height, units = "in", res = 300, bg = "white")
  } else if (output_format == "svg") {
    svglite::svglite(output_path, width = width, height = height, bg = "white")
  } else if (output_format == "pdf") {
    grDevices::pdf(output_path, width = width, height = height, bg = "white", family = FONT_FAMILY)
  } else {
    stop("Unsupported output format")
  }
}

render_output <- function(draw_expr, width, height) {
  expr <- substitute(draw_expr)
  if (is_download) {
    open_plot_device(width, height)
    on.exit(grDevices::dev.off(), add = TRUE)
    eval(expr, parent.frame())
  } else {
    cat(svglite::stringSVG({
      eval(expr, parent.frame())
    }, width = width, height = height))
  }
}

draw_blank <- function(message) {
  grid.newpage()
  grid.text(message, x = 0.5, y = 0.5, gp = gpar(fontfamily = FONT_FAMILY, fontsize = 14, col = "#666666"))
}

df <- arrow::read_parquet(heatmap_path)
if (nrow(df) == 0 || ncol(df) <= 2) {
  render_output(draw_blank("No significant differential genes for heatmap."), width = 8, height = 6)
  quit(save = "no", status = 0)
}

df <- as.data.frame(df)
sample_names <- as.character(df$sample_name)
cluster_labels <- as.factor(df$Cluster)
feature_df <- df[, setdiff(colnames(df), c("sample_name", "Cluster")), drop = FALSE]

mat <- t(as.matrix(feature_df))
colnames(mat) <- sample_names
storage.mode(mat) <- "numeric"
mat[!is.finite(mat)] <- 0

annotation_col <- data.frame(Cluster = cluster_labels)
rownames(annotation_col) <- sample_names

render_output({
  pheatmap(
    mat,
    annotation_col = annotation_col,
    show_colnames = FALSE,
    fontsize = 11,
    fontsize_row = 10,
    border_color = NA,
    scale = "none",
    cluster_cols = FALSE,
    cluster_rows = TRUE,
    color = colorRampPalette(c("#313695", "#74ADD1", "#F7F7F7", "#F46D43", "#A50026"))(100),
    main = "Top Differential Genes"
  )
}, width = 8, height = 6)
