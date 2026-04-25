# =============================================================================
# R 脚本：使用 clusterCrit 包计算 Dunn / Xie-Beni / S_Dbw 聚类评估指标
# 调用方式：Rscript analysis.R <parquet_file>
# 结果直接输出到 stdout，Python 端以 UTF-8 读取
# =============================================================================

library(arrow)
library(clusterCrit)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  cat('{"error": "Usage: Rscript analysis.R <parquet_file>"}\n')
  quit(status = 1)
}

parquet_file <- args[1]

tryCatch(
  {
    # 读取 Parquet 文件：包含 sample_name, label, emb_0, emb_1, ... 列
    df <- read_parquet(parquet_file, as_data_frame = TRUE)

    # 提取标签，强制从 1 开始（clusterCrit 要求正整数标签）
    labels <- as.integer(df$label)
    labels <- labels - min(labels) + 1L # 0-based → 1-based，同时兼容任意起始值

    # 提取嵌入矩阵（所有 emb_ 开头的列）
    emb_cols <- grep("^emb_", names(df), value = TRUE)
    embeddings <- as.matrix(df[, emb_cols])

    # 使用 clusterCrit 一次性计算三个指标
    scores <- intCriteria(
      traj = embeddings, part = labels,
      crit = c("dunn", "xie_beni", "s_dbw")
    )

    # 将结果直接输出到 stdout
    result_json <- sprintf(
      '{"dunn": %.4f, "xb": %.4f, "s_dbw": %.4f}',
      scores$dunn, scores$xie_beni, scores$s_dbw
    )
    cat(result_json, "\n")
  },
  error = function(e) {
    cat(sprintf('{"error": "%s"}', gsub('"', '\\"', as.character(e$message))))
    quit(status = 1)
  }
)
