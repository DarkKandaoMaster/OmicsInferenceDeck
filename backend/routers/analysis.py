# =============================================================================
# 接口：运行分析
# =============================================================================
import os
import datetime
import joblib
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from algorithms import load_algorithm

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
    reduction: str="PCA" #用户选择的降维算法，默认PCA

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
        # 【修改】加载 joblib 二进制字典
        file_path=os.path.join("upload",request.session_id,"omics_data.joblib")
        if not os.path.exists(file_path): #检查该路径是否存在
            # raise FileNotFoundError(f"找不到文件: {request.filename}")
            raise FileNotFoundError(f"找不到文件")
        data_dict = joblib.load(file_path)

        # 2. 动态加载算法，并传入所有的参数实例化
        algo_class = load_algorithm(request.algorithm)
        algo_instance = algo_class(
            n_clusters=request.n_clusters,
            random_state=seed,
            max_iter=request.max_iter,
            n_neighbors=request.n_neighbors
        )

        # 调用核心规范接口，算法内部负责融合、计算并返回结果
        labels,embeddings,sample_names=algo_instance.fit_predict(data_dict)



        # # 临时做法：依然在此处执行早期融合，满足目前 K-means 和谱聚类的需求。等以后你的 BaseClass 弄好了，直接把 data_dict 传进模型就行。
        # df = pd.concat(data_dict.values(), axis=1, join='inner')
        # # df=pd.read_csv(file_path,header=0,index_col=0,sep=',') #因为"/api/upload"已经处理好文件了，所以这里可以直接这么读取输入数据
        # print(f"[算法日志] 数据加载成功，形状为: {df.shape}")

        # # 2.根据用户选择的算法训练模型并获取聚类标签
        # model=None
        # if request.algorithm=="K-means": #如果用户选择了K-means算法
        #     #初始化K-means模型，同时将前端传来的用户自定义的参数传入模型
        #     model=KMeans(
        #         n_clusters=request.n_clusters,
        #         random_state=seed,
        #         max_iter=request.max_iter
        #     )
        # elif request.algorithm=="Spectral Clustering": # 【新增】谱聚类算法
        #     model=SpectralClustering(
        #         n_clusters=request.n_clusters,
        #         n_neighbors=request.n_neighbors, # 【新增】传入邻居数
        #         random_state=seed,
        #         affinity='nearest_neighbors' # 推荐使用 nearest_neighbors 构建亲和矩阵，对高维组学数据更稳定
        #     )
        # else: #如果用户选择了其他算法
        #     raise ValueError("选择了未实现的算法")
        # labels=model.fit_predict(df) #按照用户设置的参数，使用df这个输入数据，不断地训练模型。训练结束后，返回最后一次训练结果

        # 3.计算三个聚类评估指标：轮廓系数、CH指数、DB指数，它们是可以用来给任何聚类算法打分的通用指标
        metrics_scores={} #初始化一个字典，用来存放这三个指标
        if request.n_clusters>=2: #只有当簇数量大于等于2时，聚类评估指标才有数学意义
            s_score=silhouette_score(embeddings,labels) #轮廓系数。范围[-1,1]，越接近1表示分类效果越好。衡量一个样本“离自己组的人有多近”、“离隔壁组的人有多远”
            ch_score=calinski_harabasz_score(embeddings,labels) #CH指数。范围[0,+∞)，值越大表示分类效果越好。衡量簇内紧密度与簇间分离度的比值，简单来说就是它希望“组内越紧密越好”、“组间离得越远越好”
            db_score=davies_bouldin_score(embeddings,labels) #DB指数。范围[0,+∞)，值越小表示分类效果越好。衡量簇之间的重叠程度，如果这个指标很高，说明不同组混在一起了，分得不清楚
            metrics_scores={
                "silhouette": round(float(s_score),4), #将s_score强制类型转换float，然后四舍五入保留小数点后4位
                "calinski": round(float(ch_score),4),
                "davies": round(float(db_score),4)
            }
        else: #如果K<2，那么这些指标都无法计算，所以我们把这些指标都赋值为-1
            metrics_scores={
                "silhouette": -1,
                "calinski": -1,
                "davies": -1
            }

        #于是我们就计算出来那三个聚类评估指标了。但是它们不太直观，所以我们来另外计算一个散点图。如果聚类效果确实很好（样本确实分得很开），那么通常指标会很好、散点图也会分得很开，两者趋势是一致的
        # 4.为了能够画散点图，我们需要对df使用PCA/t-SNE/UMAP降维。PCA/t-SNE/UMAP搞定散点图中的x、y坐标，需要评估的算法搞定散点图中点对应的簇
        coords=None #用来存放降维后的结果
        if request.reduction=="PCA":
            coords=PCA(n_components=2,random_state=seed)   .fit_transform(embeddings) #初始化PCA模型，指定降维到2维（x轴和y轴）；对df进行降维，返回一个形状为(样本数量,2)的numpy数组。其中第0列表示第一主成分（PC1），这是数据差异最大、最能区分样本的方向；第1列表示第二主成分（PC2），这是数据差异第二大的方向
        elif request.reduction=="t-SNE":
            coords=TSNE(n_components=2,random_state=seed)   .fit_transform(embeddings)
        else: #如果用户选择了"UMAP"，或者选择了未知的降维算法，那么默认使用UMAP
            coords=umap.UMAP(n_components=2,random_state=seed)   .fit_transform(embeddings)
        plot_data=[] #初始化一个列表，用来存放每个样本对应的信息，以便前端画散点图。在前端的散点图中，每个样本对应一个点
        for i in range(len(sample_names)):
            plot_data.append({
                "name": str(sample_names[i]), #样本名称
                "x": float(coords[i,0]), #降维后的第一主成分，作为散点图中的x轴坐标
                "y": float(coords[i,1]), #降维后的第二主成分，作为散点图中的y轴坐标
                "cluster": int(labels[i]) #该样本所属的簇标签
            })

        #为结果字典赋值
        mock_result_data={
            # "method": "K-means (Real Run)",
            "method": request.algorithm,
            "n_samples": len(sample_names),
            "n_features": embeddings.shape[1],
            # "n_samples": df.shape[0], #样本总数
            # "n_features": df.shape[1], #特征数量
            "labels": labels.tolist(), #将numpy数组转换为Python列表，不然numpy数组无法直接序列化为JSON
            # "cluster_counts": pd.Series(labels).value_counts().to_dict(), #统计每个类别（簇）的样本数量
            # 👇 修改这里：使用字典推导式强制转换类型【【【【【除了列表推导式还有其他方法吗？比如使用pandas？
            "cluster_counts": {int(k): int(v) for k, v in pd.Series(labels).value_counts().items()},
            "metrics": metrics_scores, #我们刚才计算出来的聚类评估指标
            "plot_data": plot_data #存放每个样本对应的信息的那个列表
        }
        # print("[算法日志] K-means 计算完成") #在控制台打印日志

        return {
            "status": "success",
            "message": f"算法 {request.algorithm} 调用成功！",
            "server_time": datetime.datetime.now().isoformat(),
            "data": mock_result_data
        }

    except Exception as e: #处理用户参数设置不合理，或者上传了一个非常大的CSV文件并且上传时硬盘存得下但处理时硬盘存不下，等情况
        print(f"[算法错误] {str(e)}")
        # 直接抛出 400 异常，让前端 axios 能够正确捕捉到 error
        raise HTTPException(status_code=400, detail=f"算法运行失败: {str(e)}")

    #构建HTTP响应
    #下面这个字典就是要返回给前端的东西
    # response={
    #     "status": "success",
    #     "message": f"算法 {request.algorithm} 调用成功！",
    #     "server_time": datetime.datetime.now().isoformat(), #当前时间戳，格式为ISO 8601
    #     "data": mock_result_data #我们刚才操作的结果字典
    # }
    # print(f"[后端日志] 返回结果: {response['status']}")
    # return response #FastAPI会自动将这个字典序列化成JSON字符串，然后通过网络发送给前端
