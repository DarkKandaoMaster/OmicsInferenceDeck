# =============================================================================
# 接口：富集分析
# =============================================================================
import pandas as pd
import gseapy as gp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 创建路由器实例
router=APIRouter()

class EnrichmentRequest(BaseModel): #定义数据校验模型
    cluster_genes: dict[str,list[str]] #字典，键为所有簇的ID，值为簇对应的差异基因列表
    database: str #用户选择的是GO分析还是KEGG分析

@router.post("/api/enrichment_analysis")
async def run_enrichment_analysis(request:EnrichmentRequest):
    print(f"\n[后端日志] 收到富集分析请求，处理的簇数量: {len(request.cluster_genes)}")
    print(f"[后端日志] 目标数据库: {request.database}")

    try:
        if request.database=='GO': #如果前端选择GO分析，那么我们需要分别查询BP、CC、MF三个库
            gmt_files={
                "BP": './references/GO_KEGG/GO_Biological_Process_2025.gmt',
                "CC": './references/GO_KEGG/GO_Cellular_Component_2025.gmt',
                "MF": './references/GO_KEGG/GO_Molecular_Function_2025.gmt'
            }
        else: #如果前端选择KEGG分析，那么只查KEGG一个库
            gmt_files={
                "KEGG": './references/GO_KEGG/KEGG_2026.gmt'
            }

        enrichment_results={} # 初始化结果字典，用于存放形如 {"0": [...], "1": [...]} 的结果

        # 遍历前端传来的字典，针对每一个簇的基因列表分别进行富集分析
        for cluster_id, gene_list in request.cluster_genes.items():
            # 检查基因数量，如果基因太少（少于3个），富集分析跑不出来，直接返回空列表
            if len(gene_list)<3:
                print(f"[警告] Cluster {cluster_id} 基因数量太少 (<3)，跳过该簇")
                enrichment_results[cluster_id]=[] # 给该簇分配空列表，防止前端报错
                continue

            plot_data=[] # 存放当前簇最终返回给前端的画图数据

            # *********************************************
            # [修改] 遍历我们需要查询的库（GO的话会循环3次，KEGG只会循环1次）
            for category, gmt_file in gmt_files.items():
                # 使用 gseapy.enrich 进行离线富集分析
                enr=gp.enrich(
                    gene_list=gene_list, # 当前簇的差异基因列表
                    gene_sets=gmt_file,  # 当前遍历到的数据库路径
                    outdir=None, # 设置为None表示直接在内存中处理，不在本地生成多余文件
                    no_plot=True # 不生成图片，我们只需要数据结果传给前端渲染
                )

                # 提取结果 DataFrame
                results_df=enr.results

                # 如果结果不为空，进行筛选和排序
                # if not results_df.empty:
                # 【修改】增加类型检查：当 gseapy 找不到富集结果时，enr.results 会返回空列表 []，而不是 DataFrame
                if isinstance(results_df, pd.DataFrame) and not results_df.empty:
                    # 筛选出 P-value < 0.05 的显著通路，并按 P值从小到大排序
                    filtered_results=results_df[results_df["P-value"]<0.05].sort_values("P-value")

                    # 为了防止GO的三个库加起来图表太拥挤，并且像PDF里那样各展示几条，我们限制每个库取前1条；KEGG则还是取前3条
                    top_results = filtered_results.head(5) if request.database == 'GO' else filtered_results.head(3) #这里可以考虑让用户自己定义

                    # 遍历提取结果，整理成前端方便读取的字典列表格式
                    for index, row in top_results.iterrows():
                        # *********************************************
                        # [新增] 计算 Rich Factor (富集因子)，即命中的基因数除以通路总基因数，这是气泡图 X 轴的标准数据
                        overlap_str = str(row["Overlap"]) # 将 Overlap 字段（例如 "10/50"）转为字符串
                        try:
                            num, den = overlap_str.split('/') # 以斜杠为界，拆分出分子（命中的基因数）和分母（通路总基因数）
                            rich_factor = float(num) / float(den) # 计算富集因子
                        except:
                            rich_factor = 0.0 # 如果解析失败，则兜底赋值为 0.0
                        # *********************************************
                        plot_data.append({
                            "Term": row["Term"], # 通路名称
                            "P_value": row["P-value"], # 原始P值
                            "Adjusted_P": row["Adjusted P-value"], # 校正后的P值
                            "Overlap": row["Overlap"], # 重叠的基因比例
                            "Genes": row["Genes"], # 命中的具体基因名称
                            # 新增：计算命中的具体基因数量（通过分号分割 Genes 字符串），作为前端图表的X轴数值
                            "Gene_Count": len(str(row["Genes"]).split(";")),
                            # 新增：保存当前通路的分类（BP, CC, MF 或 KEGG），前端画图上色要用
                            "Category": category,
                            # [新增] 将计算好的富集因子加入返回字典中，传给前端画气泡图用
                            "Rich_Factor": rich_factor
                        })

            # 将当前簇处理好的列表，存入总结果字典中
            enrichment_results[cluster_id]=plot_data 

        print(f"[后端日志] 富集分析完成！")

        # 返回与火山图类似的嵌套结构，供前端自由切换
        return {
            "status": "success",
            "database": request.database, # 返回当前使用的数据库标识
            "data": enrichment_results # 返回包含所有簇结果的字典
        }

    except Exception as e:
        print(f"[富集分析错误] {str(e)}")
        raise HTTPException(status_code=400,detail=f"富集分析失败: {str(e)}")
