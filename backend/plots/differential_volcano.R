suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(ggplot2)
  library(svglite)
  library(grid)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript differential_volcano.R <volcano.parquet> <cluster_id> [format] [output_path]")
}

volcano_path <- args[[1]]
cluster_id <- as.integer(args[[2]])
output_format <- if (length(args) >= 3) tolower(args[[3]]) else ""
output_path <- if (length(args) >= 4) args[[4]] else ""
is_download <- output_format %in% c("png", "svg", "pdf") && nzchar(output_path)
FONT_FAMILY <- "Times New Roman"

LOGFC_THRESHOLD <- 0.5
P_THRESHOLD <- 0.05

UP_COLOR <- "#D7263D"
DOWN_COLOR <- "#1B98E0"
NS_COLOR <- "#BFC5CC"
GUIDE_COLOR <- "#6B6F76"
LABEL_COLOR <- "#1F2329"

open_plot_device <- function(width, height) {
  if (output_format == "png") {
    grDevices::png(output_path, width = width, height = height, units = "in", res = 600, bg = "white", type = "cairo")
  } else if (output_format == "svg") {
    svglite::svglite(output_path, width = width, height = height, bg = "white")
  } else if (output_format == "pdf") {
    grDevices::cairo_pdf(output_path, width = width, height = height, bg = "white", family = FONT_FAMILY)
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

# finite_max equivalent: largest finite value, falling back to a default when none exist.
finite_max <- function(values, default = 1.0) {
  finite <- values[is.finite(values)]
  if (length(finite) == 0) default else max(finite)
}

df <- as.data.frame(arrow::read_parquet(volcano_path))
df <- df[!is.na(suppressWarnings(as.integer(df$cluster))) &
         as.integer(df$cluster) == cluster_id, , drop = FALSE]
if (nrow(df) == 0) {
  render_output(draw_blank(sprintf("No differential result for Cluster %d.", cluster_id)), width = 8, height = 6)
  quit(save = "no", status = 0)
}

to_num <- function(x) suppressWarnings(as.numeric(x))
df$t_pvalue <- to_num(df$t_pvalue)
df$t_pvalue[is.na(df$t_pvalue)] <- 1.0
df$logFC <- to_num(df$logFC)
df$logFC[is.na(df$logFC)] <- 0.0
df$negLog10P <- to_num(df$negLog10P)
df$negLog10P[!is.finite(df$negLog10P)] <- 0.0

up <- df$t_pvalue < P_THRESHOLD & df$logFC > LOGFC_THRESHOLD
down <- df$t_pvalue < P_THRESHOLD & df$logFC < -LOGFC_THRESHOLD
n_up <- sum(up)
n_down <- sum(down)

ns_label <- "NS"
down_label <- sprintf("Down (%d)", n_down)
up_label <- sprintf("Up (%d)", n_up)

df$category <- ns_label
df$category[down] <- down_label
df$category[up] <- up_label
# Draw NS underneath, then Down/Up on top (mirrors the matplotlib z-order).
df$category <- factor(df$category, levels = c(ns_label, down_label, up_label))
df <- df[order(df$category), , drop = FALSE]

color_values <- c(NS_COLOR, DOWN_COLOR, UP_COLOR)
names(color_values) <- c(ns_label, down_label, up_label)
size_values <- c(1.1, 1.7, 1.7)
names(size_values) <- c(ns_label, down_label, up_label)
alpha_values <- c(0.5, 0.82, 0.82)
names(alpha_values) <- c(ns_label, down_label, up_label)

y_threshold <- -log10(P_THRESHOLD)
x_abs <- finite_max(abs(df$logFC), default = 1.0)
y_max <- finite_max(df$negLog10P, default = 1.0)

comparison <- "Cluster vs Others"
if ("comparison" %in% colnames(df)) {
  comparison_values <- df$comparison[!is.na(df$comparison)]
  if (length(comparison_values) > 0) {
    comparison <- as.character(comparison_values[[1]])
  }
}

sig <- df[df$category %in% c(down_label, up_label), , drop = FALSE]
top <- sig[order(sig$t_pvalue, -sig$negLog10P), , drop = FALSE]
top <- utils::head(top, 10)

has_ggrepel <- requireNamespace("ggrepel", quietly = TRUE)

p <- ggplot(df, aes(x = logFC, y = negLog10P, color = category, size = category, alpha = category)) +
  geom_hline(yintercept = y_threshold, color = GUIDE_COLOR, linetype = "dashed", linewidth = 0.32, alpha = 0.7) +
  geom_vline(xintercept = LOGFC_THRESHOLD, color = GUIDE_COLOR, linetype = "dashed", linewidth = 0.32, alpha = 0.7) +
  geom_vline(xintercept = -LOGFC_THRESHOLD, color = GUIDE_COLOR, linetype = "dashed", linewidth = 0.32, alpha = 0.7) +
  geom_point(shape = 16, stroke = 0) +
  scale_color_manual(values = color_values, breaks = c(ns_label, down_label, up_label), name = NULL) +
  scale_size_manual(values = size_values, guide = "none") +
  scale_alpha_manual(values = alpha_values, guide = "none") +
  scale_x_continuous(limits = c(-x_abs * 1.08, x_abs * 1.08)) +
  scale_y_continuous(limits = c(0, y_max * 1.12 + 0.1)) +
  labs(
    title = sprintf("Cluster %d: %s", cluster_id, comparison),
    x = "Log2 Fold Change",
    y = "-Log10(P-value)"
  )

if (nrow(top) > 0) {
  if (has_ggrepel) {
    # Feed every scatter point to the repel layer so labels avoid ALL points,
    # not just the labelled ones. Non-top genes get an empty label: ggrepel
    # draws nothing for them but still treats their position as an obstacle.
    repel_df <- df
    repel_df$repel_label <- ifelse(repel_df$gene %in% top$gene, as.character(repel_df$gene), "")
    p <- p + ggrepel::geom_text_repel(
      data = repel_df,
      mapping = aes(x = logFC, y = negLog10P, label = repel_label),
      inherit.aes = FALSE,
      family = FONT_FAMILY,
      fontface = "bold",
      size = 3.2,
      color = LABEL_COLOR,
      box.padding = 0.6,
      point.padding = 0.3,
      min.segment.length = 0,
      max.overlaps = Inf,
      segment.color = "#7A7F87",
      segment.size = 0.4,
      segment.alpha = 0.8
    )
  } else {
    p <- p + geom_text(
      data = top,
      mapping = aes(x = logFC, y = negLog10P, label = gene),
      inherit.aes = FALSE,
      family = FONT_FAMILY,
      fontface = "bold",
      size = 3.2,
      color = LABEL_COLOR,
      hjust = -0.1,
      vjust = -0.4
    )
  }
}

p <- p +
  guides(color = guide_legend(override.aes = list(size = 3, alpha = 1))) +
  theme_bw(base_family = FONT_FAMILY, base_size = 12) +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid.major = element_line(color = "#E5E7EB", linewidth = 0.21),
    panel.grid.minor = element_blank(),
    panel.border = element_rect(color = "#2B2F36", fill = NA, linewidth = 0.5),
    plot.title = element_text(family = FONT_FAMILY, size = 16, face = "bold", hjust = 0.5),
    axis.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
    axis.text = element_text(family = FONT_FAMILY, size = 16, face = "bold", colour = "black"),
    legend.position = c(0.985, 0.985),
    legend.justification = c(1, 1),
    legend.title = element_blank(),
    legend.text = element_text(family = FONT_FAMILY, size = 11),
    legend.background = element_rect(fill = "white", color = "black", linewidth = 0.4),
    legend.key = element_rect(fill = "white", color = NA),
    legend.margin = margin(2, 4, 2, 4)
  )

render_output(print(p), width = 8, height = 6)
