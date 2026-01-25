import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import datetime

# 1. 初始化 FastAPI 应用
# 这里我们定义了新的平台名称 InferenceDeck
app = FastAPI(
    title="InferenceDeck API Platform",
    description="Backend for Multi-Omics Cancer Subtyping Platform",
    version="0.1.0"
)

# 2. 配置 CORS (跨域资源共享) - 关键步骤
# 如果不配置这个，前端 Vue (localhost:5173) 无法访问 后端 (localhost:8000)
origins = [
    "http://localhost:5173",  # Vue 默认端口
    "http://127.0.0.1:5173",
    "*"                       # 调试阶段允许所有来源
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],      # 允许所有方法 (GET, POST, etc.)
    allow_headers=["*"],      # 允许所有 Headers
)

# 3. 定义请求体模型 (Pydantic)
# 这要严格匹配前端 axios 发送的数据结构：
# { algorithm: 'PIntMF', timestamp: '...' }
class AnalysisRequest(BaseModel):
    algorithm: str
    timestamp: str

# 4. 定义核心接口 /api/run
# 前端点击按钮后，会向这个地址发送 POST 请求
@app.post("/api/run")
async def run_analysis(request: AnalysisRequest):
    print(f"\n[后端日志] 收到分析请求:")
    print(f"   - 算法: {request.algorithm}")
    print(f"   - 时间戳: {request.timestamp}")

    # --- 模拟算法运行过程 ---
    # 在真实场景中，这里会调用您的 PyTorch/TensorFlow 模型
    # 比如：result = my_model.predict(data)
    
    time.sleep(1.5) # 模拟计算耗时 1.5秒

    # 根据选择的算法返回不同的模拟数据
    mock_result_data = {}
    
    if request.algorithm == "PIntMF":
        mock_result_data = {
            "method": "PIntMF (Matrix Factorization)",
            "clusters_found": 3,
            "accuracy_score": 0.88,
            "top_genes": ["TP53", "BRCA1", "EGFR"]
        }
    elif request.algorithm == "Subtype-GAN":
        # 这里未来可以接入您 server.py 里的 CancerSubtypePredictor
        mock_result_data = {
            "method": "Subtype-GAN (Deep Learning)",
            "clusters_found": 5,
            "convergence_epoch": 600,
            "note": "使用了生成对抗网络进行亚型识别"
        }
    else:
        mock_result_data = {
            "info": f"算法 {request.algorithm} 的接口尚未完全实现",
            "status": "pending"
        }

    # --- 构建返回给前端的响应 ---
    response = {
        "status": "success",
        "message": f"算法 {request.algorithm} 调用成功！",
        "server_time": datetime.datetime.now().isoformat(),
        "data": mock_result_data
    }
    
    print(f"[后端日志] 返回结果: {response['status']}")
    return response

# 5. 启动服务器的入口
# 运行命令: python main.py
if __name__ == "__main__":
    # host="0.0.0.0" 允许局域网访问，port=8000 是常用端口
    uvicorn.run(app, host="127.0.0.1", port=8000)