library(SNFtool)

# 接收 Python 传来的参数
args <- commandArgs(trailingOnly = TRUE)
temp_dir <- args[1]
k <- as.numeric(args[2])
labels_path <- args[3]
embed_path <- args[4]

# 静默加载 NEMO 包
suppressMessages(library(NEMO))

# 读取临时目录下的所有输入 CSV 文件
files <- list.files(temp_dir, pattern = "\\.csv$", full.names = TRUE)

data_list <- list()
for(f in files){
  # Python 导出的 CSV：行是病人，列是特征
  df <- read.csv(f, row.names = 1)
  # NEMO 严格要求：行是特征，列是病人，所以需要转置 t()
  data_list[[basename(f)]] <- t(as.matrix(df))
}

# === 运行 NEMO 核心算法 ===
# 1. 计算亲和度图 (Affinity Graph)
graph <- nemo.affinity.graph(data_list)

# 2. 执行聚类
clusters <- nemo.clustering(graph, num.clusters = k)

# 3. 导出聚类标签给 Python
labels_df <- data.frame(Cluster = clusters, row.names = names(clusters))
write.csv(labels_df, labels_path)

# 4. NEMO 同样输出的是相似度矩阵(graph)，为了画散点图，我们在 R 中对其做特征值分解(Eigen)提取低维特征
eig <- eigen(graph, symmetric = TRUE)
n_dims <- min(10, ncol(graph) - 1)
embed_mat <- eig$vectors[, 1:n_dims]
rownames(embed_mat) <- rownames(graph)
write.csv(embed_mat, embed_path)