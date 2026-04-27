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

blank_svg <- function(message) {
  svglite::stringSVG({
    grid.newpage()
    grid.text(message, x = 0.5, y = 0.5, gp = gpar(fontfamily = "serif", fontsize = 14, col = "#666666"))
  }, width = 8, height = 6)
}

df <- as.data.frame(arrow::read_parquet(data_path))
if (nrow(df) == 0) {
  cat(blank_svg("No enrichment result available."))
  quit(save = "no", status = 0)
}

df <- df %>%
  mutate(
    cluster = factor(cluster, levels = sort(unique(cluster))),
    Gene_Count = as.numeric(Gene_Count),
    Adjusted_P = as.numeric(Adjusted_P),
    Adjusted_P = ifelse(is.na(Adjusted_P) | Adjusted_P <= 0, as.numeric(P_value), Adjusted_P),
    neg_log_p = -log10(pmax(Adjusted_P, 1e-300)),
    TermShort = str_wrap(str_trunc(str_remove(Term, " \\(GO.*$"), width = 60), width = 42)
  ) %>%
  arrange(Adjusted_P) %>%
  group_by(cluster) %>%
  slice_head(n = 5) %>%
  ungroup()

if (nrow(df) == 0) {
  cat(blank_svg("No significant enrichment result available."))
  quit(save = "no", status = 0)
}

term_levels <- rev(unique(df$TermShort))
df$TermShort <- factor(df$TermShort, levels = term_levels)

if (mode == "by_gene") {
  p <- ggplot(df, aes(x = Gene_Count, y = TermShort)) +
    geom_point(aes(size = Gene_Count, color = cluster), alpha = 0.85) +
    labs(title = "Pathway Enrichment by Gene Count", x = "Gene Number", y = "Pathways", color = "Cluster", size = "Gene Number") +
    theme_bw(base_family = "serif", base_size = 14)
} else {
  p <- ggplot(df, aes(x = cluster, y = TermShort)) +
    geom_point(aes(size = Gene_Count, color = neg_log_p), alpha = 0.86) +
    scale_color_gradient(low = "#377EB8", high = "#E41A1C") +
    labs(title = "Pathway Enrichment - All Clusters", x = "Cluster", y = "Pathways", color = expression(-log[10](p.adjust)), size = "Gene Number") +
    theme_bw(base_family = "serif", base_size = 14)
}

p <- p +
  scale_size_continuous(range = c(3, 13)) +
  theme(
    text = element_text(face = "bold"),
    plot.title = element_text(hjust = 0.5, size = 16),
    axis.text.y = element_text(size = 10, lineheight = 0.85),
    legend.position = "right",
    plot.margin = margin(5, 5, 5, 5, "mm")
  )

cat(svglite::stringSVG(print(p), width = 8, height = 6))
