suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(ggplot2)
  library(stringr)
  library(svglite)
  library(grid)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("Usage: Rscript enrichment_bubble.R <enrichment.parquet> <mode> <database> [cluster_id] [dataset] [format] [output_path]")
}

data_path <- args[[1]]
mode <- args[[2]]
database <- toupper(args[[3]])
cluster_arg <- if (length(args) >= 4) as.character(args[[4]]) else "0"
dataset <- if (length(args) >= 5) trimws(args[[5]]) else ""
output_format <- if (length(args) >= 6) tolower(args[[6]]) else ""
output_path <- if (length(args) >= 7) args[[7]] else ""
is_download <- output_format %in% c("png", "svg", "pdf") && nzchar(output_path)
FONT_FAMILY <- "serif"

open_plot_device <- function(width, height) {
  if (output_format == "png") {
    grDevices::png(output_path, width = width, height = height, units = "in", res = 600, bg = "white")
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
  grid.text(message, x = 0.5, y = 0.5, gp = gpar(fontfamily = FONT_FAMILY, fontsize = 16, col = "#666666"))
}

df <- as.data.frame(arrow::read_parquet(data_path))
if (nrow(df) == 0) {
  render_output(draw_blank("No enrichment result available."), width = 8, height = 6)
  quit(save = "no", status = 0)
}

df <- df %>%
  mutate(
    cluster = factor(cluster, levels = sort(unique(cluster))),
    cluster_numeric = as.integer(as.character(cluster)),
    Gene_Count = as.numeric(Gene_Count),
    Adjusted_P = as.numeric(Adjusted_P),
    Adjusted_P = ifelse(is.na(Adjusted_P) | Adjusted_P <= 0, as.numeric(P_value), Adjusted_P),
    neg_adjusted_p = -1 * Adjusted_P,
    TermShort = str_remove(Term, " \\(GO.*$")
  ) %>%
  arrange(Adjusted_P)

if (mode == "by_gene") {
  df <- df %>%
    filter(cluster == cluster_arg)
} else {
  df <- df %>%
    group_by(cluster) %>%
    slice_head(n = 3) %>%
    ungroup()
}

if (nrow(df) == 0) {
  render_output(draw_blank("No significant enrichment result available."), width = 8, height = 6)
  quit(save = "no", status = 0)
}

if (mode == "by_gene") {
  term_levels <- rev(unique(df$TermShort))
} else {
  pathway_priority <- df %>%
    group_by(TermShort) %>%
    summarise(highest_cluster = min(cluster_numeric), .groups = "drop") %>%
    arrange(highest_cluster, TermShort)
  term_levels <- pathway_priority$TermShort
}
df$TermShort <- factor(df$TermShort, levels = term_levels)

if (mode == "by_gene") {
  by_gene_title <- if (nzchar(dataset)) {
    paste0(database, " Enrichment - ", dataset, " Cluster ", cluster_arg)
  } else {
    paste0(database, " Enrichment - Cluster ", cluster_arg)
  }
  p <- ggplot(df, aes(x = Gene_Count, y = TermShort)) +
    geom_point(aes(size = Gene_Count, color = neg_adjusted_p)) +
    scale_color_gradient(low = "green", high = "red") +
    geom_text(aes(label = Gene_Count), hjust = -0.7, size = 5.6, color = "black", family = FONT_FAMILY) +
    labs(
      title = by_gene_title,
      x = "Gene Number",
      y = "Pathways",
      color = expression(p.adjust),
      size = "Count"
    ) +
    theme_bw(base_family = FONT_FAMILY, base_size = 16)
} else {
  combined_title <- if (nzchar(dataset)) {
    paste0(database, " Pathway Enrichment - ", dataset, " All Clusters")
  } else {
    paste0(database, " Pathway Enrichment - All Clusters")
  }
  p <- ggplot(df, aes(x = cluster, y = TermShort)) +
    geom_point(aes(size = Gene_Count, color = neg_adjusted_p), alpha = 0.8) +
    scale_color_gradient(low = "blue", high = "red") +
    labs(
      title = combined_title,
      x = "Cluster",
      y = paste0(database, " Pathways"),
      color = expression(p.adjust),
      size = "Gene Count"
    ) +
    theme_bw(base_family = FONT_FAMILY, base_size = 16)
}

if (mode != "by_gene") {
  p <- p + scale_size_continuous(range = c(3, 15))
}

# 如果Y轴标签超过45个字符，那么就把它截断，显示省略号
p <- p + scale_y_discrete(labels = function(x) str_trunc(x, 45))

p <- p +
  theme(
    text = element_text(family = FONT_FAMILY, size = 16),
    axis.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
    axis.text = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
    axis.text.y = element_text(family = FONT_FAMILY, size = 16, face = "bold", lineheight = 0.8), #听AI说这个参数只对多行文本有意义，现在气泡图不折行了它就不起作用，是无害的残留
    plot.title = element_text(family = FONT_FAMILY, size = 16, face = "bold", hjust = 0.5),
    legend.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
    legend.text = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
    legend.position = "right",
    plot.margin = margin(5, 5, 5, 5, "mm"),
    panel.spacing = unit(0.1, "lines")
  )

svg_width <- if (mode == "by_gene") 10 else 12
svg_height <- if (mode == "by_gene") 8 else 10
render_output(print(p), width = svg_width, height = svg_height)
