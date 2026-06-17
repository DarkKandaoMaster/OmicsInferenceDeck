# ============================================================
# R 依赖安装脚本
#   用法（在项目根目录或任意位置）:
#     Rscript backend/install_r_packages.R
#   建议使用 R >= 4.3。Windows 上请先安装 Rtools（编译源码包需要）。
# ============================================================

repos <- "https://cloud.r-project.org"

# ---- 安装辅助函数：已存在则跳过 ----
ensure_cran <- function(pkgs) {
  for (pkg in pkgs) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      message("Installing CRAN package: ", pkg)
      install.packages(pkg, repos = repos)
    }
  }
}

ensure_bioc <- function(pkgs) {
  if (!requireNamespace("BiocManager", quietly = TRUE)) {
    install.packages("BiocManager", repos = repos)
  }
  for (pkg in pkgs) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      message("Installing Bioconductor package: ", pkg)
      BiocManager::install(pkg, update = FALSE, ask = FALSE)
    }
  }
}

ensure_github <- function(repo, pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    message("Installing GitHub package: ", repo)
    remotes::install_github(repo, upgrade = "never")
  }
}

# ---- 安装工具链 ----
ensure_cran(c("remotes"))

# ---- CRAN 包 ----
# arrow      : 读写 parquet（Python <-> R 数据交换的核心）
# 绘图        : ggplot2 / ggrepel / pheatmap / svglite / dplyr / stringr
# 聚类/指标   : cluster / clusterCrit / survival / SNFtool
ensure_cran(c(
  "arrow",
  "ggplot2",
  "ggrepel",
  "pheatmap",
  "svglite",
  "dplyr",
  "stringr",
  "cluster",
  "clusterCrit",
  "survival",
  "SNFtool",
  "gtsummary",
  "broom"
))

# ---- Bioconductor 包 ----
# 差异分析     : limma / edgeR
# 富集分析     : clusterProfiler / org.Hs.eg.db / AnnotationDbi
ensure_bioc(c(
  "limma",
  "edgeR",
  "clusterProfiler",
  "org.Hs.eg.db",
  "AnnotationDbi"
))

# ---- 算法包（多组学聚类，源码安装）----
ensure_github("Shamir-Lab/NEMO/NEMO", "NEMO")  # NEMO 算法
ensure_github("mpierrejean/pintmf", "PintMF")  # PintMF 算法

ensure_github("DXCODEE/MOSD", "MOSD")          # MOSD 算法

message("R 依赖安装流程结束。")
