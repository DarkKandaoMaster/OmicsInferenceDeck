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
  stop("Usage: Rscript enrichment_bar.R <enrichment.parquet> <cluster_id>")
}

data_path <- args[[1]]
cluster_id <- args[[2]]
FONT_FAMILY <- "serif"

blank_svg <- function(message) {
  svglite::stringSVG({
    grid.newpage()
    grid.text(message, x = 0.5, y = 0.5, gp = gpar(fontfamily = FONT_FAMILY, fontsize = 16, col = "#666666"))
  }, width = 8, height = 6)
}

df <- as.data.frame(arrow::read_parquet(data_path))
if (nrow(df) == 0) {
  cat(blank_svg("No enrichment result available."))
  quit(save = "no", status = 0)
}

df <- df %>%
  filter(as.character(cluster) == as.character(cluster_id)) %>%
  mutate(
    Gene_Count = as.numeric(Gene_Count),
    P_value = as.numeric(P_value),
    Category = ifelse(is.na(Category), "Enrichment", as.character(Category))
  ) %>%
  arrange(P_value) %>%
  group_by(Category) %>%
  slice_head(n = 5) %>%
  ungroup()

if (nrow(df) == 0) {
  cat(blank_svg(paste0("Cluster ", cluster_id, " has no significant enrichment.")))
  quit(save = "no", status = 0)
}

df <- df %>%
  mutate(
    TermShort = vapply(strsplit(str_remove(Term, " \\(GO.*$"), " "), function(words) paste(head(words, 6), collapse = " "), character(1)),
    TermShort = str_wrap(TermShort, width = 40),
    TermShort = factor(TermShort, levels = rev(unique(TermShort))),
    Category = factor(Category)
  )

palette <- c(BP = "#66C3A5", CC = "#8DA1CB", MF = "#FD8D62", KEGG = "#3498DB", Enrichment = "#3498DB")

p <- ggplot(df, aes(x = TermShort, y = Gene_Count, fill = Category)) +
  geom_col(width = 0.62) +
  geom_text(aes(label = Gene_Count), hjust = -0.2, size = 4.5, family = FONT_FAMILY) +
  coord_flip() +
  scale_fill_manual(values = palette, drop = FALSE) +
  scale_y_continuous(limits = c(0, max(df$Gene_Count) + 1)) +
  labs(title = paste0("Enrichment - Cluster ", cluster_id), x = "Terms", y = "Gene Number") +
  theme_bw(base_family = FONT_FAMILY, base_size = 16) +
  theme(
    text = element_text(family = FONT_FAMILY, size = 16),
    axis.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
    axis.text.x = element_text(family = FONT_FAMILY, size = 16),
    axis.text.y = element_text(family = FONT_FAMILY, size = 14, hjust = 1, lineheight = 0.8, margin = margin(r = 8)),
    plot.title = element_text(family = FONT_FAMILY, size = 16, face = "bold", hjust = 0.5),
    legend.title = element_blank(),
    legend.text = element_text(family = FONT_FAMILY, size = 16),
    legend.position = "right",
    plot.margin = margin(5, 5, 5, 5, "mm"),
    panel.spacing = unit(0.05, "lines"),
    axis.title.y = element_text(margin = margin(r = 15))
  )

cat(svglite::stringSVG(print(p), width = 12, height = 9))
