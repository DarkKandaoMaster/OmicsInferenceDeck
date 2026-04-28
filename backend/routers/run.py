"""运行分析，运行用户选择的聚类算法。

本文件读取 upload.py 保存的组学数据，根据前端传来的算法名称和参数加载算法，
执行聚类并生成每个样本的标签和特征矩阵。结果会保存为 cluster_result.parquet，
供 metrics.py、cluster_scatter.py、survival.py、differential.py 等后续接口使用。
"""

import os
import datetime
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from algorithms import load_algorithm
from routers.upload import OMICS_DATA_FILE, load_frame_dict

# 创建路由器实例
router=APIRouter()

class AnalysisRequest(BaseModel): #定义数据校验模型 #定义一个类，在这个类里声明几个变量，并且明确指定这几个变量的类型。以此实现确保输入数据类型符合该要求，如果不符合，FastAPI会自动拦截并返回422错误
    #这里的冒号使用的是Python的类型提示语法。 变量名: 类型 意思是声明一个名为 变量名 的变量，它的预期类型是 类型 
    #虽然在普通Python代码中类型提示通常只是像注释一样给人看的，但在pydantic.BaseModel中，冒号具有强制性，Pydantic库会读取冒号后面的类型，并像C语言那样执行强制类型转换和验证
    algorithm: str #用户选择的算法名称
    timestamp: str #请求发起时的时间戳
    session_id: str # 【修改】将 filename 改为 session_id
    # filename: str #用户上传的使用UUID改名后的组学数据文件名
    #以下参数具有默认值，所以以下参数是可选参数，其他算法即便不传这些参数也不会报错
    #K-means算法
    n_clusters: int=3 #聚类簇数（K值），默认3
    random_state: int=42 #随机种子，默认42
    max_iter: int=300 #最大迭代次数，默认300，用于防止算法在无法收敛时陷入死循环
    # 【新增】谱聚类的核心参数：邻居数
    n_neighbors: int=10
    #用户选择的降维算法
    # reduction: str="PCA" #用户选择的降维算法，默认PCA

@router.post("/api/run")
async def run_analysis(request:AnalysisRequest): #指定record的类型为AnalysisRequest，就是我们刚才定义的那个类，如果前端传来的数据类型不匹配，FastAPI会自动拦截并返回422错误
    # print(f"\n[后端日志] 收到分析请求:") #在控制台打印日志（实际生产环境中建议使用logging模块替代print）
    # print(f"   - 用户选择的算法名称: {request.algorithm}")
    # print(f"   - 时间戳: {request.timestamp}")
    # print(f"   - 用户上传的文件名: {request.filename}")
    # print(f"   - 用户选择的降维算法: {request.reduction}")
    # print(f"   - 参数: K={request.n_clusters}, Seed={request.random_state}, Iter={request.max_iter}")

    #设置全局随机种子。虽然下面这几句代码是写在函数里的，但它们生效的范围是全局。所以虽然在当前开发阶段这么写是完全可取的，但如果我以后要构建一个高并发的商业级服务器，这么写就不可取了
    seed=request.random_state if request.random_state!=-1 else None #如果用户传的是-1，变量设为None；否则设为用户传来的整数
    # random.seed(seed) # 设置Python原生random库的种子
    # np.random.seed(seed) #设置NumPy的随机种子
    # seed_for_torch=request.random_state if request.random_state!=-1 else random.randint(0,2**32-1) #pytorch比较特殊，不能直接把None作为种子，所以我们随机生成一个整数作为种子
    # torch.manual_seed(seed_for_torch) #设置CPU生成随机数的种子
    # torch.cuda.manual_seed(seed_for_torch) #为当前GPU设置随机种子
    # torch.cuda.manual_seed_all(seed_for_torch) #为所有GPU设置随机种子

    # mock_result_data={} #初始化结果字典，这个就是函数要返回的东西之一

    #接下来我们打算：
    # 1.读取"/api/upload"已经处理好的组学数据文件
    # 2.根据用户选择的算法训练模型并获取聚类标签
    # 3.计算三个聚类评估指标
    # 4.对df使用PCA/t-SNE/UMAP降维
    # 5.返回结果

    try:
        # 1.读取"/api/upload"已经处理好的组学数据文件
        # file_path=os.path.join("upload",request.filename) #"/api/upload"已经处理好的组学数据文件的所在路径
        # 加载 parquet 输入数据和 JSON 元数据
        file_path=os.path.join("upload",request.session_id,OMICS_DATA_FILE)
        if not os.path.exists(file_path): #检查该路径是否存在
            # raise FileNotFoundError(f"找不到文件: {request.filename}")
            raise FileNotFoundError(f"找不到组学数据文件，请先上传数据")
        data_dict = load_frame_dict(file_path)

        # 2. 动态加载算法，并传入所有的参数实例化
        algo_class = load_algorithm(request.algorithm)
        algo_instance = algo_class(
            n_clusters=request.n_clusters,
            random_state=seed,
            max_iter=request.max_iter,
            n_neighbors=request.n_neighbors
        )

        # 3. 运行算法，获取聚类结果
        # fit_predict 返回：
        #   labels       — 形状 (n_samples,) 的 numpy 数组，每个样本的簇标签
        #   embeddings   — 形状 (n_samples, n_features) 的 numpy 数组，用于后续评估和降维
        #   sample_names — 长度 n_samples 的列表，样本名称
        labels, embeddings, sample_names = algo_instance.fit_predict(data_dict)

        # 4. 将中间结果持久化到 cluster_result.parquet，供 /api/metrics 和 /api/plots/cluster_scatter 读取
        n_features = embeddings.shape[1]
        df_result = pd.DataFrame(
            embeddings,
            columns=[f"emb_{i}" for i in range(n_features)]
        )
        df_result.insert(0, "sample_name", sample_names)
        df_result.insert(1, "label", labels)
        result_path = os.path.join("upload", request.session_id, "cluster_result.parquet")
        df_result.to_parquet(result_path, index=False)

        # 5. 返回基础聚类信息（不含指标和散点图，由独立指标/绘图接口负责）
        return {
            "status": "success",
            "message": f"算法 {request.algorithm} 运行成功，请调用 /api/metrics 获取指标，并调用 /api/plots/cluster_scatter 获取散点图",
            "server_time": datetime.datetime.now().isoformat(),
            "data": {
                "method": request.algorithm,
                "n_samples": len(sample_names),
                "n_features": int(embeddings.shape[1]),
                "labels": labels.tolist(),
                "cluster_counts": {int(k): int(v) for k, v in pd.Series(labels).value_counts().items()},
            }
        }

    except Exception as e:
        print(f"[算法错误] {str(e)}")
        raise HTTPException(status_code=400, detail=f"算法运行失败: {str(e)}")
