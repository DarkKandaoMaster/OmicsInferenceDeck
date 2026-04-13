# =============================================================================
# 接口：测试模式（参数敏感性分析）
# =============================================================================
import os
import itertools
import joblib
import pandas as pd
import numpy as np
from lifelines.statistics import multivariate_logrank_test
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from algorithms import load_algorithm

# 创建路由器实例
router=APIRouter()

class ParameterSearchRequest(BaseModel): # 定义参数搜索请求的数据校验模型，确保前端传来的数据格式正确
    session_id: str # 【修改】
    algorithm: str # 用户选择的算法名称
    # omics_filename: str # 用户上传的组学数据文件名
    # clinical_filename: str # 用户上传的临床数据文件名（测试模式依赖生存分析计算P值，必须要有临床数据）
    param_grid: dict[str,list] # 参数网格字典，键为参数名（如n_clusters），值为测试范围的列表（如[2,3,4]）
    random_state: int = 42 # 随机种子，保证结果可复现

@router.post("/api/parameter_search")
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
