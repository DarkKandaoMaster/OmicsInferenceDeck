# 差异基因分析脚本
rm(list=ls())
library(pacman)
p_load(limma, edgeR, pheatmap)

# =============================================================================
# 配置参数
# =============================================================================
DATASET <- "BLCA"  # 数据集名称，可修改为其他数据集
BASE_FOLDER <- file.path('D:\\23ZJC\\Files\\projs\\subtype\\Subtype-MLMOSC\\新增生信实验', DATASET)

CLUSTER_NUMS <- c(0, 1, 2, 3, 4)  # 聚类编号
FCfilter <- 0.5    # logFC阈值
Pfilter <- 0.05     # FDR阈值

# 创建数据集专用文件夹
dataset_folder <- file.path(BASE_FOLDER, DATASET)
if (!dir.exists(dataset_folder)) {
  dir.create(dataset_folder, recursive = TRUE)
  cat('创建数据集目录:', dataset_folder, '\n')
}

# 提取前三项ID部分
get_id_prefix <- function(id) {
  prefix <- strsplit(id, split = "[-.]")[[1]][1:3]
  return(paste(prefix, collapse = "-"))
}

# =============================================================================
# 差异基因分析函数
# =============================================================================
get.diff.gene <- function(cluster_num, dataset = DATASET) {
  # 创建输出目录
  output_dir <- file.path(dataset_folder, paste0('cluster', cluster_num))
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
    cat('创建目录:', output_dir, '\n')
  }
  
  cluster_names <- cluster_result$sample_names[cluster_result$y_pred == cluster_num]
  cat('聚类', cluster_num, '的样本数目:', length(cluster_names), '\n')
  
  # 读取mRNA数据
  mRNA_file <- file.path(BASE_FOLDER, paste0('mRNAmatrix_', dataset, '.txt'))
  mRNAdata <- read.table(mRNA_file, header = TRUE, sep = '\t', check.names = FALSE)
  cat('mRNAdata维度:', dim(mRNAdata), '\n')
  
  # 检查是否有基因名列
  has_gene_col <- !is.numeric(mRNAdata[1,1])
  all_names <- if(has_gene_col) colnames(mRNAdata[,-1]) else colnames(mRNAdata)
  cat('检测到基因名列:', has_gene_col, '\n')
  
  # 样本匹配
  sample_prefix_cluster <- sapply(cluster_names, get_id_prefix)
  sample_prefix_mrna <- sapply(all_names, get_id_prefix)
  matching_prefixes <- intersect(sample_prefix_cluster, sample_prefix_mrna)
  cat('匹配样本数:', length(matching_prefixes), '\n')
  
  # 筛选匹配的样本列
  if(has_gene_col) {
    matched_columns <- c(TRUE, all_names %in% cluster_names | sapply(all_names, get_id_prefix) %in% matching_prefixes)
  } else {
    matched_columns <- all_names %in% cluster_names | sapply(all_names, get_id_prefix) %in% matching_prefixes
  }
  
  filtered_mRNAdata <- mRNAdata[, matched_columns]
  filtered_sample_names <- if(has_gene_col) colnames(filtered_mRNAdata)[-1] else colnames(filtered_mRNAdata)
  cat('过滤后样本数:', length(filtered_sample_names), '\n')
  
  # 样本类型判断 (TCGA编码规则: 01-09为肿瘤, 10-19为正常)
  judge <- as.numeric(substr(filtered_sample_names, 14, 15))
  tumor_count <- sum(judge >= 1 & judge <= 9, na.rm = TRUE)
  normal_count <- sum(judge >= 10 & judge <= 19, na.rm = TRUE)
  cat('肿瘤样本数:', tumor_count, '正常样本数:', normal_count, '\n')
  
  # 基因名处理 - 从rna.fea文件获取真实基因名
  dataset_rna_file <- file.path('D:\\23ZJC\\Files\\projs\\subtype\\datasets\\fea', dataset, 'rna.fea')
  gene_name_mapping <- NULL
  
  if(file.exists(dataset_rna_file)) {
    dataset_rna <- read.table(dataset_rna_file, sep = ',', header = TRUE)
    dataset_gene_names <- sapply(strsplit(dataset_rna$gene_id, '\\|'), '[', 1)
    cat('从rna.fea读取到', length(dataset_gene_names), '个基因名\n')
    
    if(has_gene_col) {
      # 如果mRNA数据有基因名列，直接使用
      mRNA_gene_names <- filtered_mRNAdata[,1]
      common_genes <- intersect(dataset_gene_names, mRNA_gene_names)
      cat('共同基因数:', length(common_genes), '\n')
      
      if(length(common_genes) > 0) {
        filtered_mRNAdata <- filtered_mRNAdata[filtered_mRNAdata[,1] %in% common_genes, ]
      }
    } else {
      # 如果mRNA数据没有基因名列，创建映射关系
      # 假设rna.fea中的基因顺序与mRNA矩阵的行顺序一致
      if(nrow(filtered_mRNAdata) == length(dataset_gene_names)) {
        gene_name_mapping <- dataset_gene_names
        cat('创建基因名映射: mRNA矩阵行数与rna.fea基因数匹配\n')
      } else {
        cat('警告: mRNA矩阵行数(', nrow(filtered_mRNAdata), ')与rna.fea基因数(', 
            length(dataset_gene_names), ')不匹配\n')
        # 取较小的数量
        min_genes <- min(nrow(filtered_mRNAdata), length(dataset_gene_names))
        gene_name_mapping <- dataset_gene_names[1:min_genes]
        filtered_mRNAdata <- filtered_mRNAdata[1:min_genes, ]
        cat('使用前', min_genes, '个基因\n')
      }
    }
  } else {
    cat('警告: 未找到', dataset, '的rna.fea文件，使用所有基因\n')
  }
  
  # 数据预处理
  tcga <- as.matrix(filtered_mRNAdata)
  if(has_gene_col) {
    rownames(tcga) <- tcga[,1]
    GeneExp <- tcga[,-1]
  } else {
    rownames(tcga) <- paste0('Gene_', 1:nrow(tcga))
    GeneExp <- tcga
  }
  
  # 转换为数值矩阵
  GeneExp_numeric <- apply(GeneExp, 2, as.numeric)
  rownames(GeneExp_numeric) <- rownames(GeneExp)
  colnames(GeneExp_numeric) <- colnames(GeneExp)
  
  # 数据清理
  TCGA <- GeneExp_numeric
  TCGA <- avereps(TCGA)  # 处理重复基因
  TCGA <- TCGA[rowMeans(TCGA) > 0, ]  # 移除表达量为0的基因
  cat('最终基因表达矩阵维度:', dim(TCGA), '\n')
  
  # 差异分析
  design <- c(rep("tumor", tumor_count), rep("normal", normal_count))
  model_design <- model.matrix(~design)
  dge_list <- DGEList(counts = TCGA, group = design)
  dge_list <- calcNormFactors(dge_list)
  dge_list <- estimateCommonDisp(dge_list)
  dge_list <- estimateTagwiseDisp(dge_list, trend = "movingave")
  
  exact_test <- exactTest(dge_list, pair = c("tumor", "normal"))
  all_genes <- topTags(exact_test, n = Inf)$table
  
  # 保存结果
  all_genes_path <- file.path(output_dir, 'all_genes.csv')
  write.csv(all_genes, all_genes_path, row.names = TRUE)
  cat('所有基因结果保存至:', all_genes_path, '\n')
  
  # 筛选差异基因
  diff_genes <- all_genes[(all_genes$FDR < Pfilter) & 
                         (abs(all_genes$logFC) >= FCfilter), ]
  
  diff_genes_path <- file.path(output_dir, 'diff_gene_cluster.csv')
  write.csv(diff_genes, diff_genes_path, row.names = TRUE)
  cat('差异基因保存至:', diff_genes_path, '(共', nrow(diff_genes), '个基因)\n')
}

# =============================================================================
# 主程序执行
# =============================================================================

# 读取聚类结果
cluster_result_file <- file.path(BASE_FOLDER, paste0('clusters_', DATASET, '.csv'))
cluster_result <- read.table(cluster_result_file, sep = ',', header = TRUE)
cat('读取聚类结果:', cluster_result_file, '\n')

# 创建聚类子目录
for(cluster_id in CLUSTER_NUMS) {
  cluster_dir <- file.path(dataset_folder, paste0('cluster', cluster_id))
  if (!dir.exists(cluster_dir)) {
    dir.create(cluster_dir, recursive = TRUE)
    cat('创建聚类目录:', cluster_dir, '\n')
  }
}

# 执行差异基因分析
cat("开始差异基因分析...\n")
for (i in CLUSTER_NUMS) {
  cat('=== 分析', DATASET, 'Cluster', i, '===\n')
  get.diff.gene(i)
  cat('Cluster', i, '分析完成\n\n')
}

cat("差异基因分析完成！结果保存在:", dataset_folder, "\n")






