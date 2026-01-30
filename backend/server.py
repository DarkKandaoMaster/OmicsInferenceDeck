import uvicorn
from fastapi import FastAPI,HTTPException,File,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import datetime
import shutil
import os
import pandas as pd
from sklearn.cluster import KMeans

#实例化FastAPI类，创建一个Web应用程序对象，它是整个后端服务的核心，负责路由分发和请求处理
# title、description、version参数用于生成自动化的交互式API文档
app=FastAPI(
    title="InferenceDeck API Platform", #设置API文档的标题，方便前端开发者查看
    description="Backend for Multi-Omics Cancer Subtyping Platform", #设置API的描述信息
    version="1.0.0" #设置版本号，用于接口版本管理
)

#配置CORS（跨域资源共享）
# 在前后端分离架构中，前端通常运行在5173端口，后端在8000端口。浏览器出于安全策略默认禁止这种跨端口请求，因此必须配置CORS中间件来显式允许
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ #允许的源列表
        "*" #通配符，表示允许所有来源访问【仅在开发调试阶段使用，生产环境需严格限制】】】】】
    ],
    allow_credentials=True, #允许跨端口请求携带Cookie或凭证【【【【【还是跨域请求？
    allow_methods=["*"], #允许所有HTTP方法（如GET、POST、PUT、DELETE等）
    allow_headers=["*"], #允许所有HTTP请求头（如Content-Type、Authorization等）【【【【【他们是谁？
)

#定义请求体模型
class AnalysisRequest(BaseModel): #定义一个类，在这个类里声明两个变量，并且明确指定这两个变量的类型。以此实现确保输入数据类型符合该要求，否则FastAPI会返回422错误
    #这里的冒号使用的是Python的类型提示语法。 变量名: 类型 意思是声明一个名为 变量名 的变量，它的预期类型是 类型 
    #虽然在普通Python代码中类型提示通常只是像注释一样给人看的，但在pydantic.BaseModel中，冒号具有强制性，Pydantic库会读取冒号后面的类型，并像C语言那样执行强制类型转换和验证
    algorithm: str #用户选择的算法名称，如“PIntMF”、“Subtype-GAN”等
    timestamp: str #请求发起的时间戳，用于日志记录或任务追踪
    # ===============================================
    filename: str # 新增：前端需要告诉后端处理哪个文件（文件名）
    # 以下参数设置默认值，以便其他算法如果不传这些参数也不会报错
    n_clusters: int = 3 # 新增：K-means的聚类簇数，默认值为3
    random_state: int = 42 # 新增：随机种子，保证结果可复现，默认42
    max_iter: int = 300 # 新增：最大迭代次数，防止死循环，默认300
    # ===============================================

#@app.post是一个装饰器，它的作用是将下面的run_analysis函数注册到Web服务器的路由表中，当用户发送 POST 方法到“/api/run”这个网址时，服务器会自动调用下面的run_analysis函数来处理
#async可以定义异步函数，允许在等待I/O操作（如模型推理、数据库查询）时不阻塞服务器主线程
@app.post("/api/run")
async def run_analysis(request: AnalysisRequest): #FastAPI 会自动读取 HTTP 请求体中的 JSON 数据，并将其作为参数传递给 record，实现接收输入数据 #参数record的类型是PatientRecord，就是我们刚才定义的那个类【【【【【等会儿等会儿，这两句注释改一下
    #在控制台打印日志。实际生产环境中建议使用logging模块替代print
    print(f"\n[后端日志] 收到分析请求:")
    print(f"   - 算法: {request.algorithm}")
    print(f"   - 时间戳: {request.timestamp}")
    # ===============================================
    print(f"   - 处理文件: {request.filename}")
    print(f"   - 参数: K={request.n_clusters}, Seed={request.random_state}, Iter={request.max_iter}")
    # ===============================================

    # 在实际项目中，这里应该去 UPLOAD_DIR 读取刚才上传的文件
    # data = load_data(os.path.join(UPLOAD_DIR, '用户上传的文件名.csv'))

    # --- 算法运行过程 ---
    # 在实际的生产代码中，此处是集成的关键点。
    # 根据《多组学癌症亚型识别相关流程.pdf》，真实的流程应该包括：
    # 1. 接收数据：读取前端上传的 .fea (特征) 和 .clinic (临床) 文件。
    # 2. 调用算法：
    #    - 如果是 'PIntMF' (R语言实现)，此处应使用 rpy2 库调用 'analysis.R' 脚本。
    #    - 如果是 'Subtype-GAN' (Python实现)，此处应加载 PyTorch 模型并执行预测逻辑。
    # 3. 生成结果：计算 p-value, 生成生存曲线 (survival.py) 等。
    # time.sleep(1.5) #强制挂起当前协程 1.5 秒，用于模拟计算耗时1.5秒

    # 根据选择的算法返回不同的模拟数据
    # mock_result_data={} #初始化模拟的返回数据字典
    # ===============================================
    # --- 算法运行过程 (修改为真实逻辑) ---
    mock_result_data = {} # 初始化结果字典

    if request.algorithm == "K-means":
        try:
            # 1. 构建文件路径
            file_path = os.path.join("upload", request.filename)

            # 2. 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"找不到文件: {request.filename}")

            # 3. 读取CSV文件
            #期望CSV文件格式为：
            # ,特征名称1,特征名称2
            # 样本名称1,10,20
            # 样本名称2,30,40
            df=pd.read_csv(file_path, header=0, index_col=0, sep=',') #使用Pandas读取CSV格式的特征文件
            # header=0: 指定第一行作为列名。于是第一行数据不会参与到运算中
            # index_col=0: 指定第一列作为行索引。于是第一列数据不会参与到运算中
            # sep=',': 指定文件分隔符为逗号

            print(f"[算法日志] 数据加载成功，形状为: {df.shape}")

            # 4. 初始化KMeans模型
            # 将前端传来的参数传入模型
            kmeans = KMeans(
                n_clusters=request.n_clusters,
                random_state=request.random_state,
                max_iter=request.max_iter
            )

            # 5. 执行聚类并获取标签
            # df直接传入即可，因为每一行是一个样本，每一列是一个基因特征
            labels=kmeans.fit_predict(df) #按用户设置的参数训练了模型，训练结束后返回最后一次聚类结果

            # 6. 构建返回结果
            mock_result_data = {
                "method": "K-means (Real Run)",
                "n_samples": df.shape[0], # 样本数量
                "n_features": df.shape[1], # 特征数量
                "inertia": float(kmeans.inertia_), # 簇内误差平方和，评估聚类效果的指标
                "labels": labels.tolist(), # 将numpy数组转换为python列表，否则无法序列化为JSON
                # 简单统计一下每个类别的样本数，方便前端展示
                "cluster_counts": pd.Series(labels).value_counts().to_dict() 
            }
            print("[算法日志] K-means 计算完成")

        except Exception as e:
            # 如果在计算过程中出错（如文件格式不对），捕获异常并返回错误信息
            print(f"[算法错误] {str(e)}")
            return {
                "status": "error", 
                "message": f"算法运行失败: {str(e)}",
                "server_time": datetime.datetime.now().isoformat()
            }
    # ===============================================

    elif request.algorithm=="PIntMF": #根据请求中的 algorithm 字段进行条件分支处理
        # PIntMF
        # 论文中提到这是一种基于矩阵分解的方法，在 BRCA 和 STAD 数据集上表现不同
        # 这里的返回数据模拟了算法输出的关键指标
        mock_result_data={
            "method": "PIntMF (Matrix Factorization)",
            "clusters_found": 3, # 模拟识别出的亚型数量
            "accuracy_score": 0.88, # 模拟的聚类准确性评分 (如 AWA 指数)
            "top_genes": ["TP53", "BRCA1", "EGFR"] # 模拟提取的差异表达基因
        }
    elif request.algorithm=="Subtype-GAN":
        # 这里未来可以接入您 server.py 里的 CancerSubtypePredictor
        # Subtype-GAN (Deep Adversarial Learning)
        # 这是一个基于深度学习的生成对抗网络模型。
        # 这里的 convergence_epoch 模拟了神经网络训练收敛的轮数。
        mock_result_data={
            "method": "Subtype-GAN (Deep Learning)",
            "clusters_found": 5,
            "convergence_epoch": 600,
            "note": "使用了生成对抗网络进行亚型识别"
        }
    else:
        # 处理未定义的算法请求，返回状态提示
        mock_result_data={
            "info": f"算法 {request.algorithm} 的接口尚未完全实现",
            "status": "pending"
        }

    # --- 构建返回给前端的响应 ---
    # --- 构建 HTTP 响应 ---
    # FastAPI 会自动将此字典序列化为 JSON 格式返回给前端。
    # 包含状态码、消息、服务器时间和具体的数据载荷 (data)。
    #函数直接返回一个Python字典
    #FastAPI框架会自动将这个字典序列化成JSON字符串，并通过网络发送给客户端
    #客户端收到的就是形如{"status": "success", ...}的JSON数据
    response={
        "status": "success",
        "message": f"算法 {request.algorithm} 调用成功！",
        "server_time": datetime.datetime.now().isoformat(), # 返回 ISO 8601 格式的时间字符串
        "data": mock_result_data
    }
    
    print(f"[后端日志] 返回结果: {response['status']}")
    return response

#处理用户上传文件的接口，将用户上传文件保存到本地
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    print(f"\n[后端日志] 收到文件上传请求: {file.filename}")

    UPLOAD_PATH="upload" #用户上传文件的保存路径
    if not os.path.exists(UPLOAD_PATH): #如果路径不存在，则创建该目录
        os.makedirs(UPLOAD_PATH)
    file_location=os.path.join(UPLOAD_PATH,file.filename) #定义用户上传文件的保存路径

    try:
        #将用户上传文件保存到本地
        with open(file_location,"wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[后端日志] 文件已保存至: {file_location}")

        return {
            "status": "success",
            "filename": file.filename,
            "filepath": file_location,
            "message": f"文件 {file.filename} 上传成功"
        }
    except Exception as e:
        print(f"[后端日志] 上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

if __name__=="__main__": #这是Python的标准入口判断。只有当这个文件被直接运行（而不是作为模块被导入）（即python server.py）时，下面的代码才会执行
    #启动Uvicorn服务器
    #我们刚才不是实例化了一个app对象嘛，现在我们将app作为参数传给Uvicorn服务器，于是当服务器收到请求时，可以找到并调用对应的有@app.post修饰的函数
    uvicorn.run(app,host="0.0.0.0",port=8000) #这句代码的意思就是让Uvicorn服务器加载app这个对象，并且在所有网卡（0.0.0.0）上监听 8000 端口，随时接收请求
    #host="0.0.0.0"对应底层Socket编程中的INADDR_ANY宏，意思是监听本机“所有”网卡接口。也就是说允许外部网络访问本服务
    #一旦执行这句代码，主线程将进入一个无限循环，持续挂起以监听网络端口。也就是说这之后的代码都执行不了了，除非进程被信号终止
    #此时你还会发现 http://127.0.0.1:8000/docs 、 http://127.0.0.1:8000/redoc 可以打开。这是FastAPI框架自带的自动生成交互式API文档功能