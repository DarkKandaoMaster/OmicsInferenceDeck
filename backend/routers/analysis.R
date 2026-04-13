# =============================================================================
# R 脚本：使用 clusterCrit 包计算 Dunn / Xie-Beni / S_Dbw 聚类评估指标
# 调用方式：Rscript analysis.R <embeddings_csv> <labels_csv>
# 结果直接输出到 stdout，Python 端以 UTF-8 读取
# =============================================================================

suppressPackageStartupMessages(library(clusterCrit))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  cat('{"error": "Usage: Rscript analysis.R <embeddings_csv> <labels_csv>"}\n')
  quit(status = 1)
}

embeddings_file <- args[1]
labels_file     <- args[2]

tryCatch({
  # 读取数据：embeddings 为 n_samples x n_features 矩阵，labels 为一列整数
  # 显式指定 UTF-8 编码读取，避免 Windows 下乱码
  embeddings <- as.matrix(read.csv(file(embeddings_file, encoding = "UTF-8"), header = FALSE))
  labels     <- as.integer(read.csv(file(labels_file, encoding = "UTF-8"), header = FALSE)[, 1])

  # 使用 clusterCrit 一次性计算三个指标
  scores <- intCriteria(traj = embeddings, part = labels,
                        crit = c("Dunn", "Xie_Beni", "S_Dbw"))

  # 将结果直接输出到 stdout
  cat(sprintf('{"dunn": %.4f, "xb": %.4f, "s_dbw": %.4f}',
              scores$dunn, scores$Xie_Beni, scores$S_Dbw))

}, error = function(e) {
  cat(sprintf('{"error": "%s"}', gsub('"', '\\"', as.character(e$message))))
  quit(status = 1)
})
