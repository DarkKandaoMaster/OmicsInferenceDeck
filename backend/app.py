import os
os.environ["OMP_NUM_THREADS"]="5" #在Windows上搭配底层MKL库运行K-means时有一个已知内存泄漏问题（当数据块少于可用线程时会触发）。因此官方警告推荐写上这句代码，强行限制底层数学库使用的CPU线程数量为5
import warnings
warnings.filterwarnings("ignore",category=FutureWarning) #忽略类别=未来警告的警告，不让这种类别的警告打印到控制台，污染日志。为什么会有这种类别的警告？就比如snfpy库在底层调用sklearn的验证函数时，还在使用旧的未来版本会弃用的参数名force_all_finite，于是sklearn会发出警告提醒你，调用一次提醒一次
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cleanup import lifespan #导入我们在./cleanup.py里写的后台定时清理任务的生命周期管理器 #这里也不能使用相对导入

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

#注册路由
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
from routers.enrichment import router as enrichment_router #导入富集分析的路由
app.include_router(enrichment_router)
from routers.parameter_search import router as parameter_search_router #导入参数敏感性分析的路由
app.include_router(parameter_search_router)