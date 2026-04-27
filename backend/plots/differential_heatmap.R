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

blank_svg <- function(message) {
  svglite::stringSVG({
    grid.newpage()
    grid.text(message, x = 0.5, y = 0.5, gp = gpar(fontfamily = "serif", fontsize = 14, col = "#666666"))
  }, width = 8, height = 6)
}

df <- arrow::read_parquet(heatmap_path)
if (nrow(df) == 0 || ncol(df) <= 2) {
  cat(blank_svg("No significant differential genes for heatmap."))
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

svg <- svglite::stringSVG({
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

cat(svg)
