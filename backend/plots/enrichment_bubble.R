suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(ggplot2)
  library(stringr)
  library(svglite)
  library(grid)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript enrichment_bubble.R <enrichment.parquet> <mode>")
}

data_path <- args[[1]]
mode <- args[[2]]
output_format <- if (length(args) >= 3) tolower(args[[3]]) else ""
output_path <- if (length(args) >= 4) args[[4]] else ""
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
    Gene_Count = as.numeric(Gene_Count),
    Adjusted_P = as.numeric(Adjusted_P),
    Adjusted_P = ifelse(is.na(Adjusted_P) | Adjusted_P <= 0, as.numeric(P_value), Adjusted_P),
    neg_adjusted_p = -1 * Adjusted_P,
    TermShort = vapply(strsplit(str_remove(Term, " \\(GO.*$"), " "), function(words) paste(head(words, 6), collapse = " "), character(1)),
    TermShort = str_wrap(TermShort, width = 40)
  ) %>%
  arrange(Adjusted_P) %>%
  group_by(cluster) %>%
  slice_head(n = 5) %>%
  ungroup()

if (nrow(df) == 0) {
  render_output(draw_blank("No significant enrichment result available."), width = 8, height = 6)
  quit(save = "no", status = 0)
}

term_levels <- rev(unique(df$TermShort))
df$TermShort <- factor(df$TermShort, levels = term_levels)

if (mode == "by_gene") {
  p <- ggplot(df, aes(x = Gene_Count, y = TermShort)) +
    geom_point(aes(size = Gene_Count, color = neg_adjusted_p), alpha = 0.8) +
    scale_color_gradient(low = "green", high = "red") +
    geom_text(aes(label = Gene_Count), hjust = -0.7, size = 5.6, color = "black", family = FONT_FAMILY) +
    labs(title = "Pathway Enrichment by Gene Count", x = "Gene Number", y = "Pathways", color = expression(p.adjust), size = "Count") +
    theme_bw(base_family = FONT_FAMILY, base_size = 16)
} else {
  p <- ggplot(df, aes(x = cluster, y = TermShort)) +
    geom_point(aes(size = Gene_Count, color = neg_adjusted_p), alpha = 0.8) +
    scale_color_gradient(low = "blue", high = "red") +
    labs(title = "Pathway Enrichment - All Clusters", x = "Cluster", y = "Pathways", color = expression(p.adjust), size = "Gene Count") +
    theme_bw(base_family = FONT_FAMILY, base_size = 16)
}

p <- p +
  scale_size_continuous(range = c(3, 15)) +
  theme(
    text = element_text(family = FONT_FAMILY, size = 16),
    axis.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
    axis.text = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
    axis.text.y = element_text(family = FONT_FAMILY, size = 16, face = "bold", lineheight = 0.8),
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
