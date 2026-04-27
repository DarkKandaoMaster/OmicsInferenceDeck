

# GO/KEGG富集分析脚本
# 加载必要的包
library(pacman)
p_load(AnnotationDbi, org.Hs.eg.db, clusterProfiler, dplyr, ggplot2, stringr)

# 字体设置 - 简化版本，避免字体错误
FONT_FAMILY <- "serif"  # 使用系统默认serif字体，通常类似Times New Roman

# 如果用户想要使用Times New Roman，可以取消下面的注释
# 但需要确保系统已安装extrafont包并导入了字体
# tryCatch({
#   library(extrafont)
#   loadfonts(device = "win", quiet = TRUE)
#   if ("Times New Roman" %in% fonts()) {
#     FONT_FAMILY <- "Times New Roman"
#   }
# }, error = function(e) {
#   cat("Times New Roman字体不可用，使用serif字体\n")
# })

cat("使用字体:", FONT_FAMILY, "\n")

# =============================================================================
# 通用保存函数
# =============================================================================
save_plot_both_formats <- function(plot, file_path, width = 8, height = 6, dpi = 600) {
  # 获取文件名（不含扩展名）
  base_name <- tools::file_path_sans_ext(file_path)
  
  # 保存PNG格式
  png_path <- paste0(base_name, ".png")
  ggsave(png_path, plot, width = width, height = height, dpi = dpi, 
         device = "png", bg = "white")
  
  # 保存PDF格式
  pdf_path <- paste0(base_name, ".pdf")
  ggsave(pdf_path, plot, width = width, height = height, dpi = dpi, 
         device = "pdf", bg = "white")
  
  cat('图表已保存: PNG -', png_path, '\n')
  cat('图表已保存: PDF -', pdf_path, '\n')
}

# =============================================================================
# 配置参数
# =============================================================================
DATASET <- "BLCA"  # 数据集名称，可修改为其他数据集
BASE_FOLDER <- 'D:\\23ZJC\\Files\\projs\\subtype\\Subtype-MLMOSC\\新增生信实验'
CLUSTER_NUMS <- c(0, 1, 2, 3, 4)  # 聚类编号

# 创建数据集专用文件夹
dataset_folder <- file.path(BASE_FOLDER, DATASET)
if (!dir.exists(dataset_folder)) {
  dir.create(dataset_folder, recursive = TRUE)
  cat('创建数据集目录:', dataset_folder, '\n')
}

# =============================================================================
# GO富集分析函数
# =============================================================================
draw_GO <- function(cluster_num, dataset = DATASET) {
  # 读取差异基因文件
  diff_path <- file.path(dataset_folder, paste0('cluster', cluster_num), 'diff_gene_cluster.csv')
  cat('读取差异文件:', diff_path, '\n')
  diff <- read.csv(diff_path, row.names = 1)  # 第一列作为行名
  
  # 获取基因名（行名）
  gene_symbols <- rownames(diff)
  cat('差异基因数量:', length(gene_symbols), '\n')
  cat('前5个基因名:', head(gene_symbols, 5), '\n')
  
  # 基因ID转换
  gene.df <- bitr(gene_symbols, fromType = "SYMBOL", toType = "ENTREZID", OrgDb = org.Hs.eg.db)
  gene <- gene.df$ENTREZID
  
  # GO富集分析 - 使用统一参数
  go_params <- list(
    gene = gene,
    OrgDb = org.Hs.eg.db,
    keyType = "ENTREZID",
    pAdjustMethod = "BH",
    minGSSize = 1,
    pvalueCutoff = 0.1,
    readable = TRUE
  )
  
  # 分别进行BP、CC、MF富集
  ego_BP <- do.call(enrichGO, c(go_params, ont = "BP"))
  ego_CC <- do.call(enrichGO, c(go_params, ont = "CC"))
  ego_MF <- do.call(enrichGO, c(go_params, ont = "MF"))
  
  # 转换为数据框
  ego_result_BP <- as.data.frame(ego_BP)
  ego_result_CC <- as.data.frame(ego_CC)
  ego_result_MF <- as.data.frame(ego_MF)
  
  # 保存结果到数据集文件夹
  output_dir <- file.path(dataset_folder, paste0('cluster', cluster_num))
  write.csv(rbind(ego_result_BP, ego_result_CC, ego_result_MF), 
            file.path(output_dir, "GO_enrichment_all.csv"), row.names = TRUE)
  
  # 选择前5个通路进行可视化，处理空结果
  display_nums <- c(
    BP = min(nrow(ego_result_BP), 5),
    CC = min(nrow(ego_result_CC), 5),
    MF = min(nrow(ego_result_MF), 5)
  )
  
  cat('各GO类别结果数量 - BP:', nrow(ego_result_BP), 'CC:', nrow(ego_result_CC), 'MF:', nrow(ego_result_MF), '\n')
  cat('选择显示数量 - BP:', display_nums[1], 'CC:', display_nums[2], 'MF:', display_nums[3], '\n')
  
  # 安全地提取数据，处理空结果的情况
  extract_go_data <- function(df, n, go_type) {
    if (nrow(df) == 0 || n == 0) {
      return(data.frame(
        ID = character(0),
        Description = character(0), 
        GeneNumber = numeric(0),
        type = character(0),
        stringsAsFactors = FALSE
      ))
    }
    
    return(data.frame(
      ID = df$ID[1:n],
      Description = df$Description[1:n],
      GeneNumber = df$Count[1:n],
      type = rep(go_type, n),
      stringsAsFactors = FALSE
    ))
  }
  
  # 分别提取各GO类别的数据
  bp_data <- extract_go_data(ego_result_BP, display_nums[1], "BP")
  cc_data <- extract_go_data(ego_result_CC, display_nums[2], "CC")
  mf_data <- extract_go_data(ego_result_MF, display_nums[3], "MF")
  
  # 合并所有数据
  go_enrich_df <- rbind(bp_data, cc_data, mf_data)
  
  # 如果没有任何富集结果，返回NULL
  if(nrow(go_enrich_df) == 0) {
    cat("Cluster", cluster_num, "没有显著的GO富集结果\n")
    return(NULL)
  }
  
  # 设置因子水平
  go_enrich_df$type <- factor(go_enrich_df$type, levels = c("BP", "CC", "MF"))
  
  # 处理描述文本（截取前6个单词并换行）
  go_enrich_df$Description <- sapply(go_enrich_df$Description, function(x) {
    words <- strsplit(x, " ")[[1]][1:6]
    paste(words[!is.na(words)], collapse = " ")
  })
  
  # 调整文本换行宽度，避免过长的标签
  go_enrich_df$go_term_wrap <- str_wrap(go_enrich_df$Description, width = 40)
  go_enrich_df$go_term_wrap <- factor(go_enrich_df$go_term_wrap, 
                                     levels = rev(go_enrich_df$go_term_wrap))
  
  # 绘制柱状图
  COLS <- c("#66C3A5", "#8DA1CB", "#FD8D62")
  plot1 <- ggplot(go_enrich_df, aes(x = go_term_wrap, y = GeneNumber, fill = type)) +
    geom_bar(stat = "identity", width = 0.6) +  # 减小柱子宽度，增加间距
    scale_fill_manual(values = COLS) +
    coord_flip() +
    labs(title = paste("GO Enrichment -", dataset, "Cluster", cluster_num),
         x = "GO Terms", y = "Gene Number") +
    geom_text(aes(label = GeneNumber), hjust = -0.2, size = 4.5, family = FONT_FAMILY) +  # 减小数字标签大小
    theme_bw() +
    scale_y_continuous(limits = c(0, max(go_enrich_df$GeneNumber) + 1)) +
    theme(
      text = element_text(family = FONT_FAMILY, size = 16),
      # 调整Y轴文本设置，减小行间距
      axis.text.y = element_text(
        family = FONT_FAMILY, 
        size = 14,  # 稍微减小字体大小
        hjust = 1, 
        lineheight = 0.8,  # 减小行间距
        margin = margin(r = 8)  # 增加右边距
      ),
      axis.text.x = element_text(family = FONT_FAMILY, size = 16),
      axis.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      plot.title = element_text(family = FONT_FAMILY, size = 16, face = "bold", hjust = 0.5),
      legend.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      legend.text = element_text(family = FONT_FAMILY, size = 16),
      # 减少四周白边并调整面板间距
      plot.margin = margin(t = 5, r = 5, b = 5, l = 5, unit = "mm"),
      panel.spacing = unit(0.05, "lines"),  # 进一步减小面板间距
      # 增加Y轴标签区域的宽度
      axis.title.y = element_text(margin = margin(r = 15))
    )
  
  return(plot1)
}
# =============================================================================
# KEGG富集分析函数
# =============================================================================
draw_KEGG <- function(cluster_num, dataset = DATASET) {
  # 读取差异基因文件
  diff_path <- file.path(dataset_folder, paste0('cluster', cluster_num), 'diff_gene_cluster.csv')
  cat('读取差异文件:', diff_path, '\n')
  diff <- read.csv(diff_path, row.names = 1)  # 第一列作为行名
  
  # 获取基因名（行名）
  gene_symbols <- rownames(diff)
  cat('差异基因数量:', length(gene_symbols), '\n')
  
  # 基因ID转换
  gene.df <- bitr(gene_symbols, fromType = "SYMBOL", toType = "ENTREZID", OrgDb = org.Hs.eg.db)
  gene <- gene.df$ENTREZID
  
  # KEGG富集分析
  kegg_res <- enrichKEGG(gene = gene, keyType = "kegg", organism = "human", 
                        qvalueCutoff = 0.05, pvalueCutoff = 0.05)
  
  hh <- as.data.frame(kegg_res)
  if (nrow(hh) == 0) {
    cat("Cluster", cluster_num, "没有显著的KEGG通路\n")
    return(NULL)
  }
  
  # 保存结果
  output_dir <- file.path(dataset_folder, paste0('cluster', cluster_num))
  write.csv(hh, file.path(output_dir, "KEGG_enrichment.csv"), row.names = TRUE)
  
  # 绘制气泡图
  hh$order <- factor(rev(1:nrow(hh)), labels = rev(hh$Description))
  
  plot2 <- ggplot(hh, aes(y = order, x = Count)) +
    geom_point(aes(size = Count, color = -1 * p.adjust)) +
    scale_color_gradient(low = "green", high = "red") +
    geom_text(aes(label = Count), hjust = -0.7, size = 5.6, color = "black", family = FONT_FAMILY) +
    labs(color = expression(p.adjust), size = "Count",
         x = "Gene Number", y = "Pathways",
         title = paste("KEGG Enrichment -", dataset, "Cluster", cluster_num)) +
    theme_bw() +
    theme(
      text = element_text(family = FONT_FAMILY, size = 16),
      axis.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      axis.text = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      plot.title = element_text(family = FONT_FAMILY, size = 16, face = "bold", hjust = 0.5),
      legend.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      legend.text = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      # 减少四周白边
      plot.margin = margin(t = 5, r = 5, b = 5, l = 5, unit = "mm"),
      panel.spacing = unit(0.1, "lines")
    )
  
  return(plot2)
}
# =============================================================================
# 收集所有聚类的KEGG结果
# =============================================================================
collect_all_KEGG <- function(cluster_num_list, dataset = DATASET) {
  all_results <- list()
  
  for (cluster_num in cluster_num_list) {
    diff_path <- file.path(dataset_folder, paste0('cluster', cluster_num), 'diff_gene_cluster.csv')
    
    if (!file.exists(diff_path)) {
      cat('文件不存在:', diff_path, '\n')
      next
    }
    
    # 读取差异基因并进行KEGG富集
    diff <- read.csv(diff_path, row.names = 1)  # 第一列作为行名
    gene_symbols <- rownames(diff)
    gene.df <- bitr(gene_symbols, fromType = "SYMBOL", toType = "ENTREZID", OrgDb = org.Hs.eg.db)
    gene <- gene.df$ENTREZID
    
    kegg_res <- enrichKEGG(gene = gene, keyType = "kegg", organism = "human", 
                          qvalueCutoff = 0.05, pvalueCutoff = 0.05)
    
    hh <- as.data.frame(kegg_res)
    if (nrow(hh) > 0) {
      hh$cluster <- cluster_num
      hh <- hh[order(hh$p.adjust), ][1:min(3, nrow(hh)), ]  # 取前3个通路
      all_results[[as.character(cluster_num)]] <- hh
    }
  }
  
  if (length(all_results) > 0) {
    combined_df <- do.call(rbind, all_results)
    rownames(combined_df) <- NULL
    return(combined_df)
  }
  return(NULL)
}
# =============================================================================
# 绘制整合的KEGG气泡图
# =============================================================================
draw_combined_KEGG <- function(combined_df, cluster_num_list, dataset = DATASET) {
  if (is.null(combined_df)) {
    cat("没有KEGG富集结果可绘制\n")
    return(NULL)
  }
  
  # 按聚类优先级排序通路
  pathway_priority <- combined_df %>%
    group_by(Description) %>%
    summarise(highest_cluster = min(cluster)) %>%
    arrange(highest_cluster, Description)
  
  combined_df$pathway_factor <- factor(combined_df$Description, 
                                      levels = pathway_priority$Description)
  combined_df$cluster <- factor(combined_df$cluster, levels = cluster_num_list)
  
  # 创建整合气泡图
  plot_combined <- ggplot(combined_df, aes(x = cluster, y = pathway_factor)) +
    geom_point(aes(size = Count, color = -1 * p.adjust), alpha = 0.8) +
    scale_color_gradient(low = "blue", high = "red") +
    scale_size_continuous(range = c(3, 15)) +
    labs(color = expression(p.adjust), size = "Gene Count",
         x = "Cluster", y = "KEGG Pathways",
         title = paste("KEGG Pathway Enrichment -", dataset, "All Clusters")) +
    theme_bw() +
    theme(
      text = element_text(family = FONT_FAMILY, size = 16),
      axis.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      axis.text = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      plot.title = element_text(family = FONT_FAMILY, size = 16, face = "bold", hjust = 0.5),
      legend.title = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      legend.text = element_text(family = FONT_FAMILY, size = 16, face = "bold"),
      legend.position = "right",
      # 减少四周白边
      plot.margin = margin(t = 5, r = 5, b = 5, l = 5, unit = "mm"),
      panel.spacing = unit(0.1, "lines")
    )
  
  # 保存到数据集文件夹（同时保存PNG和PDF）
  save_plot_both_formats(plot_combined, 
                        file.path(dataset_folder, "Combined_KEGG_enrichment"), 
                        width = 12, height = 10, dpi = 600)
  
  return(plot_combined)
}
# =============================================================================
# 主程序执行
# =============================================================================

# 1. 执行GO富集分析
cat("开始GO富集分析...\n")
for (i in CLUSTER_NUMS) {
  cat('分析Cluster', i, '\n')
  tryCatch({
    plot1 <- draw_GO(i)
    if (!is.null(plot1)) {
      # 保存到数据集文件夹（同时保存PNG和PDF）
      # 调整尺寸：增加宽度为Y轴标签提供更多空间，调整高度适应条目数量
      output_path <- file.path(dataset_folder, paste0('cluster', i), paste0("GO_enrichment_cluster", i))
      save_plot_both_formats(plot1, output_path, width = 12, height = 9, dpi = 600)
    } else {
      cat('Cluster', i, 'GO富集分析无显著结果\n')
    }
  }, error = function(e) {
    cat('Cluster', i, 'GO分析出错:', e$message, '\n')
  })
}

# 2. 执行KEGG富集分析
cat("开始KEGG富集分析...\n")
for (i in CLUSTER_NUMS) {
  cat('分析Cluster', i, '\n')
  tryCatch({
    plot2 <- draw_KEGG(i)
    if (!is.null(plot2)) {
      # 保存到数据集文件夹（同时保存PNG和PDF）
      output_path <- file.path(dataset_folder, paste0('cluster', i), paste0("KEGG_enrichment_cluster", i))
      save_plot_both_formats(plot2, output_path, width = 10, height = 8, dpi = 600)
    } else {
      cat('Cluster', i, 'KEGG富集分析无显著结果\n')
    }
  }, error = function(e) {
    cat('Cluster', i, 'KEGG分析出错:', e$message, '\n')
  })
}

# 3. 生成整合的KEGG分析
cat("生成整合KEGG分析...\n")
combined_results <- collect_all_KEGG(CLUSTER_NUMS)
if (!is.null(combined_results)) {
  combined_plot <- draw_combined_KEGG(combined_results, CLUSTER_NUMS)
  if (!is.null(combined_plot)) {
    cat('整合KEGG图表已保存\n')
  }
}

cat("富集分析完成！结果保存在:", dataset_folder, "\n")

# 

