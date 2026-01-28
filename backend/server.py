import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import datetime

# 1. 初始化 FastAPI 应用实例
# FastAPI 是一个现代、高性能的 Web 框架，用于构建 API。
# 这里实例化了一个 app 对象，它是整个后端服务的核心，负责路由分发和请求处理。
# title, description, version 参数用于生成自动化的交互式 API 文档 (Swagger UI)。
app=FastAPI(
    title="InferenceDeck API Platform",
    description="Backend for Multi-Omics Cancer Subtyping Platform", # 对应论文中 OmiCaR 平台的后端概念
    version="0.1.0"
)

# 2. 配置 CORS (跨域资源共享) 中间件
# 跨域资源共享 (CORS) 是一种基于 HTTP 头的机制，允许服务器指示除其自身以外的来源（域、协议或端口）
# 是否有权加载资源。
# 在前后端分离架构中（如 README.md 提到的 Vue + FastAPI），前端通常运行在 5173 端口，后端在 8000 端口。
# 浏览器出于安全策略（同源策略），默认禁止这种跨端口请求，因此必须配置 CORS 中间件来显式允许。
# 如果不配置这个，前端 Vue (localhost:5173) 无法访问 后端 (localhost:8000)
origins=[
    "http://localhost:5173", # Vue 开发服务器的默认地址
    "http://127.0.0.1:5173", # 本地回环地址
    "*"                      # 通配符，表示允许任何来源访问（仅在开发调试阶段使用，生产环境需严格限制）
]

# 将 CORSMiddleware 添加到应用中间件堆栈中
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # 允许的源列表
    allow_credentials=True, # 允许跨域请求携带 Cookie 或凭证
    allow_methods=["*"], # 允许所有的 HTTP 方法 (如 GET, POST, PUT, DELETE 等)
    allow_headers=["*"], # 允许所有的 HTTP 请求头 (如 Content-Type, Authorization 等)
)

# 3. 定义数据传输对象 (DTO) / 请求体模型
# 3. 定义请求体模型 (Pydantic)
# 使用 Pydantic 的 BaseModel 进行数据验证和解析。
# 该类定义了前端发送给后端的 JSON 数据结构。FastAPI 会自动验证请求体是否符合此结构。
# 如果前端发送的数据类型不匹配（例如 algorithm 不是字符串），FastAPI 会自动返回 422 错误。
# 这要严格匹配前端 axios 发送的数据结构：
# { algorithm: 'PIntMF', timestamp: '...' }
class AnalysisRequest(BaseModel):
    algorithm: str # 用户选择的算法名称，如论文中提到的 'PIntMF', 'Subtype-GAN' 等
    timestamp: str # 请求发起的时间戳，用于日志记录或任务追踪

# 4. 定义核心接口 /api/run
# 前端点击按钮后，会向这个地址发送 POST 请求
# 4. 定义核心业务接口 /api/run
# @app.post 装饰器将 HTTP POST 请求映射到 run_analysis 函数。
# POST 方法通常用于提交数据以进行处理（此处为提交算法任务）。
# async def 定义了一个异步函数，允许在等待 I/O 操作（如模型推理、数据库查询）时不阻塞服务器主线程。
@app.post("/api/run")
async def run_analysis(request: AnalysisRequest):
    # 使用 f-string 格式化日志输出，用于后端调试。
    # 在实际生产环境中，建议使用 logging 模块替代 print。
    print(f"\n[后端日志] 收到分析请求:")
    print(f"   - 算法: {request.algorithm}")
    print(f"   - 时间戳: {request.timestamp}")

    # --- 模拟算法运行过程 ---
    # 在真实场景中，这里会调用您的 PyTorch/TensorFlow 模型
    # 比如：result = my_model.predict(data)
    # --- 模拟算法运行过程 ---
    # 在实际的生产代码中，此处是集成的关键点。
    # 根据《多组学癌症亚型识别相关流程.pdf》，真实的流程应该包括：
    # 1. 接收数据：读取前端上传的 .fea (特征) 和 .clinic (临床) 文件。
    # 2. 调用算法：
    #    - 如果是 'PIntMF' (R语言实现)，此处应使用 rpy2 库调用 'analysis.R' 脚本。
    #    - 如果是 'Subtype-GAN' (Python实现)，此处应加载 PyTorch 模型并执行预测逻辑。
    # 3. 生成结果：计算 p-value, 生成生存曲线 (survival.py) 等。
    
    # time.sleep(1.5) 强制挂起当前协程 1.5 秒，用于模拟深度学习或矩阵分解算法的高计算耗时。
    time.sleep(1.5) # 模拟计算耗时 1.5秒

    # 根据选择的算法返回不同的模拟数据
    mock_result_data={}    # 初始化模拟的返回数据字典
    
    if request.algorithm=="PIntMF": # 根据请求中的 algorithm 字段进行条件分支处理
        # PIntMF (Penalized Integrative Matrix Factorization)
        # 论文中提到这是一种基于矩阵分解的方法，在 BRCA 和 STAD 数据集上表现不同。
        # 这里的返回数据模拟了算法输出的关键指标。
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
    response={
        "status": "success",
        "message": f"算法 {request.algorithm} 调用成功！",
        "server_time": datetime.datetime.now().isoformat(), # 返回 ISO 8601 格式的时间字符串
        "data": mock_result_data
    }
    
    print(f"[后端日志] 返回结果: {response['status']}")
    return response

# 5. 应用入口点
# 当此文件作为主程序直接运行 (python server.py) 时，执行以下代码。
# 如果此文件被作为模块导入，则不执行。
# 5. 启动服务器的入口
# 运行命令: python main.py
if __name__=="__main__":
    # 使用 uvicorn 启动 ASGI 服务器。
    # app: 对应上面实例化的 FastAPI 对象。
    # host="127.0.0.1": 绑定到本地回环地址，仅允许本机访问。若需局域网访问需改为 "0.0.0.0"。
    # port=8000: 指定服务监听的端口号，前端请求需发送到此端口。
    # host="0.0.0.0" 允许局域网访问，port=8000 是常用端口
    uvicorn.run(app, host="127.0.0.1", port=8000)