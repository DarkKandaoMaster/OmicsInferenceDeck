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
    TermShort = str_wrap(str_remove(Term, " \\(GO.*$"), width = 42),
    TermShort = factor(TermShort, levels = rev(unique(TermShort))),
    Category = factor(Category)
  )

palette <- c(BP = "#66C3A5", CC = "#8DA1CB", MF = "#FD8D62", KEGG = "#3498DB", Enrichment = "#3498DB")

p <- ggplot(df, aes(x = TermShort, y = Gene_Count, fill = Category)) +
  geom_col(width = 0.62) +
  geom_text(aes(label = Gene_Count), hjust = -0.18, size = 4, family = "serif") +
  coord_flip() +
  scale_fill_manual(values = palette, drop = FALSE) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.16))) +
  labs(title = paste0("Enrichment - Cluster ", cluster_id), x = "Terms", y = "Gene Number") +
  theme_bw(base_family = "serif", base_size = 14) +
  theme(
    text = element_text(face = "bold"),
    plot.title = element_text(hjust = 0.5, size = 16),
    axis.text.y = element_text(size = 10, lineheight = 0.85),
    legend.title = element_blank(),
    legend.position = "right",
    plot.margin = margin(5, 5, 5, 5, "mm")
  )

cat(svglite::stringSVG(print(p), width = 8, height = 6))
