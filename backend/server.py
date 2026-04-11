import os
os.environ["OMP_NUM_THREADS"]="5" #在Windows上搭配底层MKL库运行K-means时有一个已知内存泄漏问题（当数据块少于可用线程时会触发）。因此官方警告推荐写上这句代码，强行限制底层数学库使用的CPU线程数量为5
import warnings
warnings.filterwarnings("ignore",category=FutureWarning) #忽略类别=未来警告的警告，不让这种类别的警告打印到控制台，污染日志。为什么会有这种类别的警告？就比如snfpy库在底层调用sklearn的验证函数时，还在使用旧的未来版本会弃用的参数名force_all_finite，于是sklearn会发出警告提醒你，调用一次提醒一次
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from scipy import stats
import gseapy as gp
import itertools
import joblib
from algorithms import load_algorithm #导入我们在./algorithms/__init__.py里写的load_algorithm函数 #这里也不能使用相对导入
from cleanup import lifespan #导入我们在./cleanup.py里写的后台定时清理任务的生命周期管理器

# =============================================================================
# 应用程序初始化
# =============================================================================
#实例化FastAPI类
#FastAPI是一个基于Python的现代、高性能Web框架，用于构建API
#这里的app对象是整个后端服务的入口，负责接收HTTP请求、路由分发和响应处理
#FastAPI框架不是会自带一个自动生成交互式API文档功能嘛，对于这个API文档我们可以设置下面这些参数title、description、version
app=FastAPI(
    title="InferenceDeck API Platform", #设置API文档的标题
    description="Backend for Multi-Omics Cancer Subtyping Platform", #设置API的描述信息
    version="1.0.0", #设置版本号
    lifespan=lifespan # <--- 【新增】挂载生命周期管理器
)

#配置CORS（跨域资源共享）中间件
#在前后端分离架构中，前端通常运行在5173端口，后端在8000端口。浏览器出于安全策略默认禁止这种跨端口请求，因此必须配置CORS中间件来显式允许
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ #允许的源列表
        "*" #通配符，表示允许任何域名访问（仅在开发调试阶段使用，生产环境需严格限制）
    ],
    allow_credentials=True, #允许请求携带凭证（如Cookies、Authorization头）
    allow_methods=["*"], #允许的HTTP方法（GET、POST、PUT、DELETE、OPTIONS等）
    allow_headers=["*"], #允许的HTTP请求头（Content-Type、Accept等）
)

# 注册路由
from routers.cleanup import router as cleanup_router #导入清理会话垃圾文件的路由
app.include_router(cleanup_router)
from routers.upload import router as upload_router #导入上传文件的路由
app.include_router(upload_router)
from routers.analysis import router as analysis_router #导入运行分析的路由
app.include_router(analysis_router)
from routers.evaluate import router as evaluate_router #导入自定义算法结果评估的路由
app.include_router(evaluate_router)
from routers.survival import router as survival_router #导入生存分析的路由
app.include_router(survival_router)
from routers.differential import router as differential_router #导入差异表达分析的路由
app.include_router(differential_router)

# =============================================================================
# 接口：富集分析
# =============================================================================
class EnrichmentRequest(BaseModel): #定义数据校验模型
    cluster_genes: dict[str,list[str]] #字典，键为所有簇的ID，值为簇对应的差异基因列表
    database: str #用户选择的是GO分析还是KEGG分析

@app.post("/api/enrichment_analysis")
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

# *********************************************
# [新增] 接口：测试模式（参数敏感性分析）
# =============================================================================
class ParameterSearchRequest(BaseModel): # 定义参数搜索请求的数据校验模型，确保前端传来的数据格式正确
    session_id: str # 【修改】
    algorithm: str # 用户选择的算法名称
    # omics_filename: str # 用户上传的组学数据文件名
    # clinical_filename: str # 用户上传的临床数据文件名（测试模式依赖生存分析计算P值，必须要有临床数据）
    param_grid: dict[str,list] # 参数网格字典，键为参数名（如n_clusters），值为测试范围的列表（如[2,3,4]）
    random_state: int = 42 # 随机种子，保证结果可复现

@app.post("/api/parameter_search")
async def run_parameter_search(request: ParameterSearchRequest):
    print(f"\n[后端日志] 收到参数敏感性分析请求，算法: {request.algorithm}")

    try:
        omics_path = os.path.join("upload", request.session_id, "omics_data.joblib")
        clinical_path = os.path.join("upload", request.session_id, "clinical_data.joblib")
        # if not os.path.exists(omics_path) or not os.path.exists(clinical_path):
        #     raise FileNotFoundError("找不到数据文件，请确保组学与临床数据均已上传。")
        # 1. 读取组学数据文件，并处理为 DataFrame
        # omics_path = os.path.join("upload", request.omics_filename)
        if not os.path.exists(omics_path):
            raise FileNotFoundError("找不到组学数据文件")
        # omics_df = pd.read_csv(omics_path, header=0, index_col=0, sep=',')
        # 2. 读取临床数据文件，并处理为 DataFrame
        # clinical_path = os.path.join("upload", request.clinical_filename)
        if not os.path.exists(clinical_path):
            raise FileNotFoundError("找不到临床数据文件")
        # clinical_df = pd.read_csv(clinical_path, header=0, index_col=0, sep=',')
        omics_dict = joblib.load(omics_path)
        # omics_df = pd.concat(omics_dict.values(), axis=1, join='inner')
        clinical_dict = joblib.load(clinical_path)
        clinical_df = list(clinical_dict.values())[0]

        # # 3. 将组学数据和临床数据按样本名称进行内连接（取交集），确保样本对齐
        # merged_df = clinical_df.join(omics_df, how="inner")【【【【【之后这里可以检查一下
        # if merged_df.empty:
        #     raise ValueError("组学数据和临床数据的样本没有交集，无法分析")

        # 提取仅包含组学特征的矩阵数据，用于聚类模型的输入
        # X = merged_df[omics_df.columns]

        # 动态加载并锁定当前要测试的算法
        algo_class = load_algorithm(request.algorithm)

        # 4. 根据前端传来的参数网格，生成所有可能的参数组合
        param_names = list(request.param_grid.keys()) # 提取所有的参数名（例如：['n_clusters', 'max_iter']）
        param_values = list(request.param_grid.values()) # 提取所有的参数取值列表（例如：[[2,3,4], [100,200,300]]）
        # 使用 itertools.product 生成笛卡尔积组合，生成形如 (2, 100), (2, 200) ... 的所有排列组合
        combinations = list(itertools.product(*param_values))
        
        results = [] # 初始化列表，用于存放所有参数组合的得分
        best_score = -1 # 初始化最佳得分（得分我们将用 -Log10(P-value) 表示，越大越好，P值越小越显著）
        best_params = None # 初始化最佳参数组合
        
        # 5. 遍历每一种参数组合，运行模型并打分
        for combo in combinations:
            # 将参数名和当前组合的值打包成字典，方便传入模型，形如 {"n_clusters": 2, "max_iter": 100}
            params = dict(zip(param_names, combo))

            # 补齐随机种子以确保结果可复现
            params['random_state'] = request.random_state
            # 实例化当前参数组合下的算法模型
            algo_instance = algo_class(**params)
            # # 初始化模型，目前示例仅支持 K-means
            # if request.algorithm == "K-means":
            #     # 将从前端传来的可能被解析为浮点数的参数强制转换为整数
            #     model = KMeans(
            #         n_clusters=int(params.get("n_clusters", 3)), 
            #         max_iter=int(params.get("max_iter", 300)), 
            #         random_state=request.random_state
            #     )
            # elif request.algorithm == "Spectral Clustering": # 【新增】谱聚类参数搜索
            #     model = SpectralClustering(
            #         n_clusters=int(params.get("n_clusters", 3)),
            #         n_neighbors=int(params.get("n_neighbors", 10)), # 【新增】动态获取参数网格中的邻居数
            #         random_state=request.random_state,
            #         affinity='nearest_neighbors'
            #     )
            # else:
            #     raise ValueError("你选的算法还没有实现")

            # 训练模型并直接获取样本对应的聚类标签
            # labels = model.fit_predict(X)
            
            # 根据当前的聚类标签计算临床生存 Log-Rank P-value
            try:
                # 只需把字典扔进去跑，获取聚类结果和对齐后的样本名
                labels, _, sample_names = algo_instance.fit_predict(omics_dict)

                # 将该次算法跑出的样本名及标签建立 DataFrame，与外部的临床数据取交集
                cluster_df = pd.DataFrame({"Cluster": labels}, index=sample_names)
                merged_for_survival = clinical_df.join(cluster_df, how="inner")

                if merged_for_survival.empty:
                    raise ValueError("样本无法对齐")

                # 调用生存分析函数计算分组的生存差异显著性
                lr_results = multivariate_logrank_test(merged_for_survival["OS.time"],merged_for_survival["Cluster"],merged_for_survival["OS"])
                p_val = lr_results.p_value
                # 将 P 值转换为 -Log10(P-value)，如果 P 值为 0，加上 1e-300 防止计算负无穷报错
                score = -np.log10(p_val + 1e-300)
            except Exception as e:
                # 如果某个参数导致某一个簇的样本只有1个，生存分析会报错，将该参数的得分设为0
                score = 0
            
            # 将当前参数组合和对应的得分记录到结果列表中
            # results.append({"params": params, "score": score})
            results.append({"params": {k: v for k, v in params.items() if k != 'random_state'}, "score": score})
            
            # 比较并更新全局最佳得分和最佳参数组合
            if score > best_score:
                best_score = score
                best_params = {k: v for k, v in params.items() if k != 'random_state'}
                
        # 6. 返回全部组合结果及最优结果给前端
        return {
            "status": "success",
            "best_params": best_params, # 最佳参数组合
            "best_score": best_score, # 最佳组合对应的 -Log10(P-value)
            "all_results": results # 所有参数组合及其得分数组，用于前端绘制 2D/3D 敏感性图
        }
    except Exception as e:
        # print(f"[参数搜索错误] {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))