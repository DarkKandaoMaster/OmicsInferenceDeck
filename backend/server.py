import os
os.environ["OMP_NUM_THREADS"]="5" #在Windows上搭配底层MKL库运行K-means时有一个已知内存泄漏问题（当数据块少于可用线程时会触发）。因此官方警告推荐写上这句代码，强行限制底层数学库使用的CPU线程数量为5
import warnings
warnings.filterwarnings("ignore",category=FutureWarning) #忽略类别=未来警告的警告，不让这种类别的警告打印到控制台，污染日志。为什么会有这种类别的警告？就比如snfpy库在底层调用sklearn的验证函数时，还在使用旧的未来版本会弃用的参数名force_all_finite，于是sklearn会发出警告提醒你，调用一次提醒一次
import uvicorn
from fastapi import FastAPI,HTTPException,File,UploadFile,Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import datetime
import shutil
import pandas as pd
import numpy as np
import uuid
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import random
import torch
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from typing import List
from scipy import stats
import gseapy as gp
import itertools
import joblib
import importlib
import json
import asyncio
import time
from contextlib import asynccontextmanager
from .algorithms import load_algorithm #导入我们在./algorithms/__init__.py里写的load_algorithm函数

# =============================================================================
# 后台定时清理任务
# =============================================================================
async def cleanup_expired_folders():
    """每隔6小时自动运行一次，清理超过6小时未修改的会话文件夹"""
    cleanup_interval = 6 * 60 * 60  # 6小时（转换为秒）这个语法非常关键，它会让这个 while True 循环每执行一次就休眠 6 小时。由于是 await 异步休眠，在这 6 小时内 CPU 会去全速处理其他用户的 API 请求，完全没有任何性能损耗。
    
    while True:
        # 挂起当前任务 6 小时（不阻塞服务器处理其他请求）
        await asyncio.sleep(cleanup_interval)
        
        upload_dir = "upload"
        if not os.path.exists(upload_dir):
            continue
            
        print(f"\n[后台任务] 开始清理 {upload_dir} 下的过期文件夹...")
        current_time = time.time()
        
        # 遍历 upload 文件夹下的所有内容
        for folder_name in os.listdir(upload_dir):
            folder_path = os.path.join(upload_dir, folder_name)
            
            # 确保它是一个文件夹
            if os.path.isdir(folder_path):
                # 获取文件夹的最后修改时间（Linux/Windows通用，getmtime 最稳妥）
                folder_mtime = os.path.getmtime(folder_path)
                
                # 判断：当前时间 - 文件夹最后修改时间 > 6 小时
                if current_time - folder_mtime > cleanup_interval:
                    try:
                        shutil.rmtree(folder_path)
                        print(f"[后台任务] 成功删除过期文件夹: {folder_name}")
                    except Exception as e:
                        print(f"[后台任务] 删除过期文件夹 {folder_name} 失败: {str(e)}")

# 定义 FastAPI 的生命周期管理器
@asynccontextmanager #这是目前 FastAPI 官方推荐的处理“服务器启动/关闭事件”的标准做法，用于替代旧版本会报警告的 @app.on_event("startup") 装饰器。
async def lifespan(app: FastAPI):
    # 【启动服务器时】创建并启动后台清理任务
    task = asyncio.create_task(cleanup_expired_folders())
    yield  # 交出控制权，让 FastAPI 正常启动并处理请求
    # 【关闭服务器时】取消清理任务，优雅退出
    task.cancel()

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

# =============================================================================
# 接口：处理用户上传组学和临床数据的接口
# =============================================================================
#@app.post是一个装饰器，它的作用是将下面的upload_file函数注册到Web服务器的路由表中，当用户发送POST请求到“/api/upload”这个网址时，服务器会自动调用下面的upload_file函数来处理，同时FastAPI会自动读取HTTP请求体中的数据，并将其传给upload_file函数中的形参，实现接收输入数据
#async可以定义异步函数，允许在进行文件读写或等待模型推理时，服务器可以挂起当前任务去处理其他请求，提高并发吞吐量
@app.post("/api/upload")
async def upload_file(   files:List[UploadFile]=File(...)   ,   data_format:str=Form(...)   ,   file_type:str=Form("omics")   ,   session_id:str=Form(...)   ,   omics_mapping:str=Form("{}")   ): #接收用户上传的组学文件和临床文件
# <--- 【新增】接收前端传来的组学映射 JSON 字符串，默认为空字典字符串
#files是用户上传的文件对象；data_format是用户选择的数据格式；file_type标记用户上传的文件是组学数据还是临床数据，默认组学；session_id是会话ID #(...)表示该对象必填，前端传来的东西必须包含该对象

    print(f"\n[日志] 接口 /api/upload 开始调用。会话ID：{session_id}")

    #接下来我们打算：【【【【【
    # 1.把各个文件都保存到本地
    # 2.根据用户选择的数据格式读取各个文件
    # 3.把读取到的各个文件合并成一个文件
    # 4.检查一下合并后的文件内容合不合规
    # 5.把合并后的文件保存到本地
    # 6.删除用户上传的各个文件
    # 7.返回结果

    UPLOAD_PATH=os.path.join("upload",session_id) #会话ID为session_id的用户的上传文件临时保存目录
    if not os.path.exists(UPLOAD_PATH): #如果该目录不存在
        os.makedirs(UPLOAD_PATH) #创建该目录
    data_dict={} #             【新增】用于包装读取后的 DataFrame，键名为文件名【【【【【
    temp_file_paths=[] #记录用户上传的各个原始文件的路径，以便后续删除这些文件

    # 【新增】解析组学映射关系
    try:
        mapping = json.loads(omics_mapping)
    except json.JSONDecodeError:
        mapping = {}

    try:
        for file in files: #遍历用户上传的每一个文件

            # 1.把用户上传的各个文件都保存到本地
            # 1. 此时 file.filename 已经是前端传来的 UUID 了
            file_location=os.path.join(UPLOAD_PATH,file.filename) #得到该文件的保存路径 【【【【【目前我没有使用uuid将该文件改名，以及之后把df_single放进字典时键名也是该文件名，这是因为之后可能有算法处理数据时是不同组学不同处理方式的，我打算根据文件名来判断对应文件是什么组学。以后要不要在前端加个选项？
            temp_file_paths.append(file_location) #记录该文件的路径，以便后续删除这些文件
            with open(file_location,"wb") as buffer: #open(file_location,"wb")表示在file_location这个路径打开或新建一个文件，"wb"表示写入二进制数据；with ... as buffer是Python的上下文管理器，于是无论后续写入是否成功，它都会在操作结束后自动关闭文件。buffer是给打开的本地文件流（就是file_location这个路径）起的名字
                shutil.copyfileobj(file.file,buffer) #可以将file.file这个文件对象复制到buffer。于是实现把文件保存到本地磁盘的指定路径中

            # 2.根据用户选择的数据格式读取各个文件（因为用户可能会把文件后缀名改成.fea之类的，所以我们不检查文件后缀名）
            df_single=None
            need_transpose=False #标记是否需要转置
            read_params={ #因为之后需要使用pd.read_csv或pd.read_excel来读文件，所以这里用一个字典read_params来存储其参数
                "sep": None, #分隔符，默认None，表示自动嗅探分隔符
                "engine": "python", #使用Python引擎，这样才能支持自动嗅探分隔符
                "header": 0, #指定表头行为第0行，表示有表头
                "index_col": 0 #指定索引列为第0列，表示有索引列
            }
            if data_format=="row_sample_yes_yes": #如果前端传过来的data_format为"row_sample_yes_yes"
                # ,特征1,特征2,特征3,...
                # 病人1,11,12,13
                # 病人2,21,22,23
                # 病人3,31,32,33
                # ...
                pass
            elif data_format=="row_sample_yes_no":
                # 特征1,特征2,特征3,...
                # 11,12,13
                # 21,22,23
                # 31,32,33
                # ...
                read_params["index_col"]=None #不指定索引列，于是读取文件时pandas会自动生成索引列0,1,2,...
            elif data_format=="row_sample_no_yes":
                # 病人1,11,12,13,...
                # 病人2,21,22,23
                # 病人3,31,32,33
                # ...
                read_params["header"]=None #不指定表头行，于是读取文件时pandas会自动生成表头行0,1,2,...
            elif data_format=="row_sample_no_no":
                # 11,12,13,...
                # 21,22,23
                # 31,32,33
                # ...
                read_params["header"]=None
                read_params["index_col"]=None
            elif data_format=="row_feature_yes_yes":
                # ,病人1,病人2,病人3,...
                # 特征1,11,21,31
                # 特征2,12,22,32
                # 特征3,13,23,33
                # ...
                need_transpose=True
            elif data_format=="row_feature_yes_no":
                # 病人1,病人2,病人3,...
                # 11,21,31
                # 12,22,32
                # 13,23,33
                # ...
                read_params["index_col"]=None
                need_transpose=True
            elif data_format=="row_feature_no_yes":
                # 特征1,11,21,31,...
                # 特征2,12,22,32
                # 特征3,13,23,33
                # ...
                read_params["header"]=None
                need_transpose=True
            elif data_format=="row_feature_no_no":
                # 11,21,31,...
                # 12,22,32
                # 13,23,33
                # ...
                read_params["header"]=None
                read_params["index_col"]=None
                need_transpose=True
            try: #首先我们尝试用pd.read_csv读文件
                df_single=pd.read_csv(file_location,**read_params)
                #**是Python的字典解包语法，可以把 字典键值对 拆解成 函数参数 
                #假设有一个函数需要两个参数：def hanshu(a,b)
                #普通调用方式：hanshu(a=1,b=2)
                #使用**的调用方式：hanshu(**{"a":1,"b":2})
            except: #如果读取失败，那么尝试用pd.read_excel读文件。不过pd.read_excel不支持sep和engine参数，所以我们先来删除它们 #注意想要使用pd.read_excel的话需要安装openpyxl库
                del read_params["sep"]
                del read_params["engine"]
                try:
                    df_single=pd.read_excel(file_location,**read_params)
                except Exception as e_read: #如果还是读取失败，那么抛出的错误会被最外层的except Exception as e捕获，删除用户上传的各个文件同时抛出HTTPException
                    raise ValueError(f"文件 {file.filename} 解析失败: {str(e_read)}") #注意因为这里的文件名是使用uuid改名后的，所以以后或许可以考虑一下，显示用户上传的原始文件名而不是使用uuid改名后的文件名？【【【【【
            if need_transpose: #如果需要转置
                df_single=df_single.T

            # 【修改】获取基础的组学类型，作为 data_dict 的键名
            if file_type == "omics":
                # 根据文件名(UUID)在映射字典中找类型，找不到默认Unknown
                base_type = mapping.get(file.filename, "Unknown")

                # 修改特征名称（列名）！格式：特征名称_组学【【【【【我当初为什么会把特征名称改名的来着？？不改名然后直接用字典的键来区分不是更好？
                df_single.columns = [f"{col}_{base_type}" for col in df_single.columns]

                # 【新增】同组学类型自动合并机制
                # 把df_single存入字典，键名类似于"mRNA", "DNA Methylation", "Unknown"
                if base_type in data_dict: #如果该组学类型的键名已存在，直接按特征列拼接（取样本交集）
                    data_dict[base_type] = pd.concat([data_dict[base_type], df_single], axis=1, join='inner')
                else: # 如果不存在，正常存入
                    data_dict[base_type] = df_single
            else: # 临床数据保持用原文件名或其他标识，且不修改列名
                data_dict[file.filename] = df_single

            # #此时df_single就很标准了，行代表病人，列代表特征。有表头行、有索引列
            # data_dict[file.filename]=df_single #将读取到的df_single存入字典data_dict

        # 3.循环结束，此时字典data_dict里面应该就已经存放好了读取到并且处理好的各个文件，所以我们来临时合并一下，检查合并后的文件内容合不合规，有没有脏数据什么的
        dataframes=list(data_dict.values())
        if not dataframes:
            raise ValueError("未上传有效文件")

        # 【新增】计算取交集前，所有文件包含的“去重样本总数”
        all_samples = set()
        for df in dataframes:
            all_samples.update(df.index)
        total_unique_samples = len(all_samples)

        df_concat=pd.concat(dataframes,axis=1,join='inner') #axis=1表示在每一行后面拼接，即按列拼接；join='inner'表示取索引的交集，即“如果病人名称有对不上的，那么取病人名称的交集”
        if df_concat.empty:
            raise ValueError("合并后数据为空！请检查数据格式选项是否正确，以及所有文件的病人名称是否一致。")

        # 【新增】计算被过滤掉的“丢失”样本数
        intersected_samples = len(df_concat.index)
        lost_samples = total_unique_samples - intersected_samples

        try:
            if df_concat.shape[1]<1: #确保df_concat至少有一列特征数据，防止读到内容为空或者仅有样本名称的文件
                raise ValueError("未检测到有效的数据列。")
            if df_concat.index.has_duplicates: #检查df_concat样本名称是否重复
                raise ValueError(f"合并后发现重复样本名: {   df_concat.index[df_concat.index.duplicated()].unique().tolist()   }。") #这样可以获取具体的重复样本名
            if df_concat.columns.has_duplicates: #检查df_concat特征名称是否重复
                raise ValueError(f"合并后发现重复特征名: {   df_concat.columns[df_concat.columns.duplicated()].unique().tolist()   }。")
            if file_type=="omics": #如果是组学数据，那么检查整个表格中是否有缺失值、是否有非数字内容
                if df_concat.isnull().sum().sum()>0: #.isnull()会返回一个和原表格形状完全相同的新表格，其中原表格是空值的地方显示True，不是空值的地方显示False，然后再对它.sum().sum()就可以得到原表格中空值的总数了
                    raise ValueError(f"检测到数据中包含 {df_concat.isnull().sum().sum()} 个缺失值，请手动清理或补全数据。")
                non_numeric_cols=df_concat.select_dtypes(exclude=[np.number]).columns.tolist() #.select_dtypes(exclude=[np.number])可以筛选出所有非数字类型（非int、float）的列
                if len(non_numeric_cols)>0:
                    raise ValueError(f"检测到以下列包含非数字内容: {non_numeric_cols}。请确保除表头行索引列外，其他所有单元格均为数字。")
            else: #如果是临床数据，那么检查OS、OS.time这两列数据中是否有缺失值、是否有非数字内容
                if 'OS' not in df_concat.columns or 'OS.time' not in df_concat.columns: #检查有没有"OS"、"OS.time"两列
                    raise ValueError("临床数据必须包含 'OS' (生存状态，1=死亡，0=存活) 和 'OS.time' (生存时间) 两列。")
                if df_concat[['OS','OS.time']].isnull().sum().sum()>0:
                    raise ValueError(f"检测到 'OS' 或 'OS.time' 列包含 {df_concat[['OS','OS.time']].isnull().sum().sum()} 个缺失值，请手动清理或补全数据。")
                non_numeric_cols=df_concat[['OS','OS.time']].select_dtypes(exclude=[np.number]).columns.tolist()
                if len(non_numeric_cols)>0:
                    raise ValueError(f"检测到以下列包含非数字内容: {non_numeric_cols}。请确保这两个列只包含数字。")

            # 接下来我们要把字典data_dict保存为joblib二进制文件
            final_file_location=os.path.join(UPLOAD_PATH,   "omics_data.joblib" if file_type=="omics" else "clinical_data.joblib"   )
            if os.path.exists(final_file_location): #如果已经存在该类型文件（omics_data.joblib或者clinical_data.joblib），那么说明这是用户重新上传该类型文件，需要先删除旧的本地文件
                os.remove(final_file_location)
            joblib.dump(data_dict, final_file_location)
            # # 5.接下来我们要把合并后的文件保存到本地
            # final_filename=f"{uuid.uuid4()}.csv" #给合并后的文件起个名
            # final_file_location=os.path.join(UPLOAD_PATH,final_filename) #得到合并后的文件的保存路径
            # df.to_csv(final_file_location) #把合并后的文件保存到本地
            # #此时保存下来的df就很标准了，行代表病人，列代表特征。有表头行、有索引列
            # #保存下来的文件，分隔符使用的是英文逗号，因为to_csv()函数的默认分隔符就是英文逗号
            # #这样一来，"/api/run"接口就可以直接使用pd.read_csv(file_path,header=0,index_col=0,sep=',')读取输入数据了

            # 6.删除用户上传的各个文件
            for path in temp_file_paths:
                if os.path.exists(path):
                    os.remove(path)

        except Exception as e:
            raise HTTPException(status_code=400,detail=f"数据格式错误: {str(e)}")
        return{
            "status": "success",
            # "filename": final_filename, #合并后的文件名称
            "original_filename": " + ".join([f.filename for f in files]), #用户上传的各个文件的原始名称。用于前端界面展示【【【【【这句代码是什么意思？
            # "filepath": final_file_location, #合并后的文件的路径
            "original_shape": None, #这个之后删掉【【【【【
            # "final_shape": df.shape, #最终用于分析的文件形状
            "lost_samples": lost_samples, # 👇 【新增】将丢失的样本数发送给前端
            "message": f"成功合并 {len(files)} 个文件"
        }
    except HTTPException as he: #捕获到了我们刚才自己抛出的错误，说明虽然读取、合并文件成功，但是文件内容不合规
        for path in temp_file_paths: #删除用户上传的各个文件
            if os.path.exists(path):
                os.remove(path)
        print(f"[后端日志] 校验不通过，文件已删除: {str(he)}")
        raise he #直接抛出错误给前端
    except Exception as e: #说明读取文件失败，或者其他什么错误
        for path in temp_file_paths: #删除用户上传的各个文件
            if os.path.exists(path):
                os.remove(path)
        print(f"[后端日志] 严重错误，文件已删除: {str(e)}")
        raise HTTPException(status_code=500,detail=f"服务器内部错误: {str(e)}") #抛出错误给前端

# =============================================================================
# 接口：清理会话垃圾文件
# =============================================================================
@app.post("/api/cleanup")
async def cleanup_session(session_id: str = Form(...)):
    """处理前端页面关闭、刷新时发来的清理请求"""
    session_path = os.path.join("upload", session_id)
    if os.path.exists(session_path):
        try:
            shutil.rmtree(session_path) # 递归删除该 session_id 下的所有文件和文件夹
            print(f"\n[后端日志] 垃圾清理成功: 会话 {session_id} 的临时文件夹已删除")
        except Exception as e:
            print(f"\n[后端日志] 垃圾清理失败: 无法删除会话 {session_id} - {str(e)}")
    return {"status": "success", "message": "Session cleaned up"}

# =============================================================================
# 接口：运行分析
# =============================================================================
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

@app.post("/api/run")
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

# =============================================================================
# 接口：自定义算法结果评估
# =============================================================================
@app.post("/api/evaluate_custom")
async def evaluate_custom(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    reduction: str = Form("PCA"),
    random_state: int = Form(42) #以后要不让用户自定义这个随机种子？【【【【【
):
    print(f"\n[后端日志] 收到自定义结果评估请求，会话ID：{session_id}")
    temp_paths = []
    try:
        UPLOAD_PATH = os.path.join("upload", session_id)
        if not os.path.exists(UPLOAD_PATH):
            os.makedirs(UPLOAD_PATH)

        file_location = os.path.join(UPLOAD_PATH, file.filename)
        temp_paths.append(file_location)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. 读取文件（包含表头行 header=0，索引列 index_col=0）
        try:
            df = pd.read_csv(file_location, index_col=0, header=0)
        except:
            try:
                df = pd.read_excel(file_location, index_col=0, header=0)
            except Exception as e:
                raise ValueError(f"结果文件解析失败，请确保格式正确: {str(e)}")

        if df.shape[1] < 2:
            raise ValueError("结果数据格式不符：除样本名称(索引列)外，至少应包含一列聚类标签和一列特征数据。")

        # 2. 提取数据（第1列是聚类标签，后续所有列是特征矩阵）
        sample_names = df.index.astype(str).tolist()
        # labels = df.iloc[:, 0].values
        # embeddings = df.iloc[:, 1:].values

        # 3. ---------- 校验交集 ----------
        valid_samples = set(sample_names)

        # 如果用户也上传了组学数据，计算与组学数据的交集
        omics_path = os.path.join(UPLOAD_PATH, "omics_data.joblib")
        if os.path.exists(omics_path):
            omics_dict = joblib.load(omics_path)
            omics_samples = set()
            for o_df in omics_dict.values():
                if not omics_samples:
                    omics_samples = set(o_df.index.astype(str))
                else:
                    omics_samples = omics_samples.intersection(set(o_df.index.astype(str)))
            valid_samples = valid_samples.intersection(omics_samples)

        # 如果用户也上传了临床数据，计算与临床数据的交集
        clinical_path = os.path.join(UPLOAD_PATH, "clinical_data.joblib")
        if os.path.exists(clinical_path):
            clinical_dict = joblib.load(clinical_path)
            clinical_df = list(clinical_dict.values())[0]
            clinical_samples = set(clinical_df.index.astype(str))
            valid_samples = valid_samples.intersection(clinical_samples)

        # 【核心修改】：计算丢失样本，不直接报错（除非全丢了）
        lost_samples = len(sample_names) - len(valid_samples)
        if len(valid_samples) == 0:
            raise ValueError("交集校验失败！结果数据中的病人在您上传的组学或临床数据中均未找到匹配。")
        
        # 过滤数据，仅保留有交集的样本
        df_filtered = df[df.index.astype(str).isin(valid_samples)]
        filtered_sample_names = df_filtered.index.astype(str).tolist()
        labels = df_filtered.iloc[:, 0].values
        embeddings = df_filtered.iloc[:, 1:].values

        # 4. ---------- 计算评估指标 ----------
        metrics_scores = {}
        if len(np.unique(labels)) >= 2:
            s_score = silhouette_score(embeddings, labels)
            ch_score = calinski_harabasz_score(embeddings, labels)
            db_score = davies_bouldin_score(embeddings, labels)
            metrics_scores = {
                "silhouette": round(float(s_score), 4),
                "calinski": round(float(ch_score), 4),
                "davies": round(float(db_score), 4)
            }
        else:
            metrics_scores = {"silhouette": -1, "calinski": -1, "davies": -1}

        # 5. ---------- 降维可视化 ----------
        seed = random_state if random_state != -1 else None
        coords = None
        if reduction == "PCA":
            coords = PCA(n_components=2, random_state=seed).fit_transform(embeddings)
        elif reduction == "t-SNE":
            coords = TSNE(n_components=2, random_state=seed).fit_transform(embeddings)
        else:
            coords = umap.UMAP(n_components=2, random_state=seed).fit_transform(embeddings)

        plot_data = []
        for i in range(len(filtered_sample_names)):
            plot_data.append({
                "name": str(filtered_sample_names[i]),
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
                "cluster": int(labels[i])
            })

        mock_result_data = {
            "method": "Custom Evaluation",
            "n_samples": len(filtered_sample_names),
            "n_features": embeddings.shape[1],
            "labels": [int(l) for l in labels],
            "cluster_counts": {int(k): int(v) for k, v in pd.Series(labels).value_counts().items()},
            "metrics": metrics_scores,
            "plot_data": plot_data,
            "lost_samples": lost_samples # 👇 新增：将丢失的样本数发给前端
        }

        # 清理临时结果文件
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)

        return {
            "status": "success",
            "message": "自定义结果评估成功！",
            "server_time": datetime.datetime.now().isoformat(),
            "data": mock_result_data
        }

    except Exception as e:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)
        print(f"[自定义评估错误] {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# 接口：生存分析
# =============================================================================
class SurvivalRequest(BaseModel): #定义数据校验模型
    # clinical_filename: str #用户上传的使用UUID改名后的临床数据文件名
    session_id: str # 【修改】
    sample: list[str] #样本名称列表
    labels: list[int] #和样本名称列表一一对应的聚类标签列表

@app.post("/api/survival_analysis")
async def run_survival_analysis(request:SurvivalRequest):
    # print(f"\n[后端日志] 收到生存分析请求，处理文件: {request.clinical_filename}")

    #接下来我们打算：
    # 1.读取"/api/upload"已经处理好的临床数据文件，得到clinical_df
    # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_df
    # 3.把clinical_df和cluster_df合并起来
    # 4.计算Log-Rank P-value
    # 5.计算绘制生存曲线所需数据
    # 6.返回结果

    try:
        # 1.读取"/api/upload"已经处理好的临床数据文件
        # clinical_path=os.path.join("upload",request.clinical_filename) #"/api/upload"已经处理好的组学数据文件的所在路径
        clinical_path=os.path.join("upload",request.session_id,"clinical_data.joblib")
        if not os.path.exists(clinical_path):
            raise FileNotFoundError("找不到临床数据文件")
        clinical_dict = joblib.load(clinical_path)
        clinical_df = list(clinical_dict.values())[0] # 取出唯一的一份临床数据
        # clinical_df=pd.read_csv(clinical_path,header=0,index_col=0,sep=',') #因为"/api/upload"已经处理好文件了，所以这里可以直接这么读取输入数据

        # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_df
        #创建一个DataFrame对象，同时传入一个字典。于是字典的key就会变成列名，value就会变成列的数据
        cluster_df=pd.DataFrame({
            "SampleID": request.sample, #样本名称列表
            "Cluster": request.labels #聚类标签列表
        })
        cluster_df.set_index("SampleID",inplace=True) #.set_index()可以将cluster_df的"SampleID"列设置为索引列；inplace=True表示直接在原对象上修改

        # 3.把clinical_df和cluster_df合并起来
        merged_df=clinical_df.join(cluster_df,how="inner") #how='inner'表示取索引的交集，即“如果病人名称有对不上的，那么取病人名称的交集”
        if merged_df.empty:
            raise ValueError("临床数据与组学数据的样本名称没有交集，无法进行分析。请检查选择的数据格式是否正确，或者样本ID是否一致。")

        # 👇 【新增】计算因为没有对应临床数据而被丢弃的聚类样本数
        lost_samples = len(cluster_df) - len(merged_df)

        # 4.计算Log-Rank P-value
        #我们来解释一下，在统计学中，我们做检验通常是为了验证一个假设：你提供的分组标签对生存时间没有任何影响
        #于是下面这个函数multivariate_logrank_test就可以根据我们传进去的三个数据，计算出一个概率（P值），告诉你上述假设成立的可能性有多大。如果P值<0.05，说明原假设大概率是错的，分组标签是有意义的
        results=multivariate_logrank_test(
            merged_df["OS.time"], #生存时间（代表病人从诊断开始到死亡或最后一次随访的时间长度）
            merged_df["Cluster"], #分组标签（根据用户选择算法算出来的分组标签）
            merged_df["OS"] #生存状态（1代表死亡，或者说事件发生；0代表存活，或者说删失）
        )
        p_value=results.p_value #得到P值

        #于是我们就计算出来P值了。但它也不太直观，所以我们来另外计算一个生存曲线。如果聚类效果确实很好（样本确实分得很开），那么通常P值会很小、生存曲线也会分得很开，两者趋势是一致的
        #总的来说，三个聚类评估指标、散点图可以看数学上分得好不好，有没有把数据分开；P值、生存曲线可以看医学上有没意义，分出来的组能不能预测病人的死活
        # 5.计算绘制生存曲线所需数据
        kmf=KaplanMeierFitter() #用来计算绘制生存曲线所需数据
        plot_data=[] #用来存放绘制生存曲线所需数据
        for cluster_id in sorted(merged_df["Cluster"].unique()): #遍历所有簇，分别计算其生存曲线 #.unique()可以获取merged_df["Cluster"]中所有不重复的值，即获取所有簇；sorted()可以升序排序
            subset=merged_df[merged_df["Cluster"]==cluster_id] #筛选出merged_df中属于当前簇的样本
            kmf.fit(subset["OS.time"],subset["OS"],label=f"Cluster {cluster_id}") #使用传入的OS.time、OS数据计算生存概率；label用于标记这条曲线的名称
            #此时使用kmf.survival_function_就能返回一个DataFrame，索引代表时间轴、列代表生存概率、列名代表上一句代码中我们传入的label。当然，整个DataFrame只有一列数据
            #接下来我们来计算删失点的坐标
            censored_times=subset[subset["OS"]==0]   ["OS.time"].tolist() #筛选出subset中删失（OS==0）的样本，取OS.time那一列，把那一列转换为列表并返回
            censored_probs=kmf.survival_function_at_times(censored_times).values.tolist() #获取删失点对应的生存概率 #.survival_function_at_times()返回的是pandas.Series，需要用.values转换为numpy数组
            plot_data.append({
                "name": f"Cluster {cluster_id}", #这条曲线的名称
                "times": kmf.survival_function_.index.tolist(), #时间轴，作为生存曲线中的x轴坐标
                "probs": kmf.survival_function_[f"Cluster {cluster_id}"].tolist(), #生存概率，作为生存曲线中的y轴坐标
                "censored_times": censored_times, #删失点的OS.time，作为删失点的x轴坐标
                "censored_probs": censored_probs #删失点对应的生存概率，作为删失点的y轴坐标
            })

        return{
            "status": "success",
            "p_value": p_value, #P值
            "km_data": plot_data, #绘制生存曲线所需数据
            "n_samples": len(merged_df), #合并后的行数，即合并后的样本数量
            "lost_samples": lost_samples # 👇 【新增】返回丢弃数量
        }
    except Exception as e:
        print(f"[生存分析错误] {str(e)}")
        raise HTTPException(status_code=400,detail=str(e))

# =============================================================================
# 接口：差异表达分析
# =============================================================================
class DifferentialAnalysisRequest(BaseModel): #定义数据校验模型
    # omics_filename: str #用户上传的使用UUID改名后的组学数据文件名
    session_id: str # 【修改】
    omics_type: str # 👈 【新增】让前端指定要使用哪个组学进行差异分析
    sample: list[str] #样本名称列表
    labels: list[int] #和样本名称列表一一对应的聚类标签列表

@app.post("/api/differential_analysis")
async def run_differential_analysis(request:DifferentialAnalysisRequest):
    # print(f"\n[后端日志] 收到差异分析请求，处理文件: {request.omics_filename}")

    #接下来我们打算：
    # 1.读取"/api/upload"已经处理好的组学数据文件，得到df
    # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_info
    # 3.把df和cluster_info合并起来，得到merged_df
    # 4.计算差异倍数（Log2 Fold Change）。这是火山图的x轴数据
    # 5.计算T检验P值，然后把它处理成-Log10(P-value)。这是火山图的y轴数据
    # 6.保存用来绘制火山图的数据。然后就已经可以绘制火山图了
    # 7.筛选一下数据，每个簇挑10个基因名称（特征名称）。这是差异基因热图的y轴数据
    # 8.在merged_df中把刚才挑出来的基因名称、以及"Cluster"列筛选出来，然后计算Z-score。这个Z-score决定了差异基因热图对应位置的颜色
    # 9.整理一下我们刚才得到的数据，然后提取样本名称、样本对应的簇。这个样本名称就是差异基因热图的x轴数据。也就是说如果你输入了1031个样本，差异基因热图的x轴就会有1031列
    # 10.然后我们再整理一下刚才得到的数据，得到差异基因热图中所有点对应的坐标和Z-score。然后就已经可以绘制差异基因热图了
    # 11.返回结果

    try:
        # 1.读取"/api/upload"已经处理好的组学数据文件
        # file_path=os.path.join("upload",request.omics_filename) #"/api/upload"已经处理好的组学数据文件的所在路径
        file_path = os.path.join("upload", request.session_id, "omics_data.joblib")
        if not os.path.exists(file_path):
            raise FileNotFoundError("找不到组学数据文件")
        # df=pd.read_csv(file_path,header=0,index_col=0,sep=',') #因为"/api/upload"已经处理好文件了，所以这里可以直接这么读取输入数据
        data_dict = joblib.load(file_path)
        # 👈 【修改】不再拼接所有文件，而是提取指定的单一组学数据
        # 👈 【修改】支持提取指定的单一组学数据，或者拼接所有组学数据
        if request.omics_type == "All (Concatenated)":
            # 将 data_dict 中所有的 DataFrame 按列拼接（取样本的交集）
            df = pd.concat(list(data_dict.values()), axis=1, join='inner')
        else:
            if request.omics_type not in data_dict:
                raise ValueError(f"未找到指定的组学数据类型: {request.omics_type}")
            df = data_dict[request.omics_type]
            # 👇 【新增】根据前端传来的 omics_type，去掉对应的组学后缀名
            # 注意：使用 endswith 和切片，防止基因名中间刚好包含后缀字符被误删
            # 根据前端传来的omics_type，把组学后缀名去掉。但如果omics_type为All，那么不删
            suffix = f"_{request.omics_type}"
            df.columns=[     col[:-len(suffix)] if str(col).endswith(suffix) else col     for col in df.columns]
            # [ ... for col in df.columns ]
            # 这是 Python 的列表推导式。它的意思是：把 df.columns（原数据表的所有列名）里的每一个列名拿出来，记作 col，然后通过前面的规则处理它，最后把处理完的所有名字打包成一个新的列表。

        # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_info
        #创建一个DataFrame对象，同时传入一个字典。于是字典的key就会变成列名，value就会变成列的数据
        cluster_info=pd.DataFrame({
            "SampleID": request.sample, #样本名称列表
            "Cluster": request.labels #聚类标签列表
        })
        cluster_info.set_index("SampleID",inplace=True) #.set_index()可以将cluster_info的"SampleID"列设置为索引列；inplace=True表示直接在原对象上修改

        # 3.把df和cluster_info合并起来，得到merged_df
        merged_df=df.join(cluster_info,how="inner") #how='inner'表示取索引的交集，即“如果病人名称有对不上的，那么取病人名称的交集”
        if merged_df.empty:
            raise ValueError("样本名称无法匹配，请检查数据一致性。")

        genes=merged_df.columns[:-1] #获取所有特征名称，也就是获取除了最后一列之外的所有列名。因为最后一列是我们刚刚加进去的"Cluster"
        unique_clusters=sorted(merged_df["Cluster"].unique()) #获取簇编号。先获取merged_df中"Cluster"列的值，然后对它去除重复值，再对它排个序。结果类似于[0,1,2]
        volcano_data={} #存放每个簇的用来绘制火山图的数据
        top_genes_set=set() #存放后面筛选出来的基因名称（特征名称）。这是差异基因热图的y轴数据

        #遍历每一个簇，进行“一对多”比较，找出每个簇特有的特征【【【【【以后或许可以在这里加一个“一对一”比较
        for target_cluster in unique_clusters:
            group_a_df=merged_df[merged_df["Cluster"]==target_cluster][genes] #首先筛选出属于当前簇的样本，然后只保留所有特征列
            group_b_df=merged_df[merged_df["Cluster"]!=target_cluster][genes] #首先筛选出不属于当前簇的样本，然后只保留所有特征列
            if len(group_a_df)<2 or len(group_b_df)<2: #如果任意一组样本数量少于2，就没法做T检验
                print(f"[警告] Cluster {target_cluster} 样本数不足，跳过该簇")
                volcano_data[int(target_cluster)]=[] #给这个簇一个空列表，防止前端报错
                continue
            # 4.计算差异倍数（Log2 Fold Change）。这是火山图的x轴数据
            mean_a=group_a_df.mean(axis=0) #对a组每一列求平均值
            mean_b=group_b_df.mean(axis=0) #对b组每一列求平均值
            log_fc=mean_a-mean_b #pandas会自动按索引对齐相减 #这里我们先假设数据已经log2处理过，于是log2(A)-log2(B)=log2(A/B)，这样就能计算出差异倍数。下载下来的数据集一般都是已经Log2处理过的 #如果是原始count数据，这里应该用np.log2(mean_a/mean_b)【【【【【看看学长的代码有没有处理Log2

            # 5.计算T检验P值，然后把它处理成-Log10(P-value)。这是火山图的y轴数据
            t_stat,t_pvalue=stats.ttest_ind(group_a_df,group_b_df,axis=0,equal_var=False,nan_policy='omit') #比较a组和b组的每一列数据，得到T检验P值。equal_var=False表示不假设两组方差相等；nan_policy='omit'表示如果数据中有缺失值，那么自动忽略，防止报错
            #我们先把刚才计算出来的东西放进pd.DataFrame里，方便后续处理
            cluster_res_df=pd.DataFrame({ #还是和之前一样，字典的key就会变成列名，value就会变成列的数据
                "gene": genes,
                "logFC": log_fc.values, #.values可以把pandas.Series转换成numpy数组
                "t_pvalue": t_pvalue #把原始T检验P值也传给前端，于是前端会把t_pvalue<0.05的点涂成红色和蓝色，其他点涂成灰色
            })
            cluster_res_df["t_pvalue"]=cluster_res_df["t_pvalue"].fillna(1.0) #计算出的T检验P值可能含有NaN，所以我们来处理一下它，把NaN填为1.0（最大值，代表完全不显著）
            cluster_res_df["negLog10P"]=-np.log10(cluster_res_df["t_pvalue"]+1e-300) #然后我们把它-log10一下，就能得到-Log10(P-value)。加上1e-300是为了防止P值为0时算出负无穷，于是无法绘图

            # 6.保存用来绘制火山图的数据。此时就已经可以绘制火山图了
            volcano_data[int(target_cluster)]=cluster_res_df.to_dict(orient="records") #.to_dict(orient="records")可以把pd.DataFrame转换为字典列表，也就是[{"gene":"A","logFC":...},{"gene":"B"...}]

            # 7.筛选一下数据，每个簇挑10个基因名称（特征名称）。这是差异基因热图的y轴数据
            top_genes_set.update(   cluster_res_df[(cluster_res_df["t_pvalue"]<0.05)&(cluster_res_df["logFC"]>0)]   .sort_values(by="logFC",ascending=False).head(10)["gene"].tolist()   ) #首先筛选出cluster_res_df中t_pvalue<0.05且logFC>0的数据，然后把它们按"LogFC"列降序排序，取前10行，然后只保留"gene"列，然后转换成列表，最后.update()会自动把列表中的元素逐个加入集合，并自动去重

        # 8.在merged_df中把刚才挑出来的基因名称、以及"Cluster"列筛选出来，然后计算Z-score。这个Z-score决定了差异基因热图对应位置的颜色
        top_genes_list=list(top_genes_set) #首先我们把top_genes_set集合转换成列表
        if not top_genes_list: #如果列表为空，那么直接返回空热图数据
            print("[警告] 未检测到显著差异基因，返回空热图数据")
            return{
                "status": "success",
                "volcano_data": volcano_data,
                "heatmap_data": {"samples":[],"sample_labels":[],"genes":[],"values":[]}
            }
        heatmap_df=merged_df[top_genes_list+["Cluster"]].copy() #首先把两个列表top_genes_list、["Cluster"]拼接一下，然后在merged_df中把这些列筛选出来，最后.copy()一下
        #为什么这里要用.copy()？因为Pandas有一个很容易让人困惑的机制：视图（View）vs副本（Copy）。不知道的话自己去搜，反正你只要知道：
        # 修改数据时我们最好不要在原始数据上修改，而是创建一个副本，在副本上修改。基于这个原则：
        #  不修改具体单元格的值（比如筛选、排序、改列名、计算平均值）：可以不用.copy()。因为它们默认情况下会直接返回一个新DataFrame对象，不会修改原始数据
        #  要修改具体单元格的值：必须用.copy()。不然会修改原始数据，Pandas也会弹出著名的SettingWithCopyWarning警告
        heatmap_df[top_genes_list]=( heatmap_df[top_genes_list] - heatmap_df[top_genes_list].mean() ) / heatmap_df[top_genes_list].std() #首先在heatmap_df中把top_genes_list这些列筛选出来（因为不能让"Cluster"列也参与运算），然后计算Z-score：(值-平均值)/标准差，最后把它赋值回去。这是能减得起来的，因为Pandas有广播机制 #此时这些值都会被压缩到大致-2 ~ 2的区间内

        # 9.整理一下我们刚才得到的数据，然后提取样本名称、样本对应的簇。这个样本名称就是差异基因热图的x轴数据
        heatmap_df=heatmap_df.sort_values(by="Cluster") #把heatmap_df按"Cluster"列升序排序，这样就能把同一个簇的数据排在一起
        sorted_samples=heatmap_df.index.tolist() #提取样本名称（也就是行索引）
        sorted_labels=heatmap_df["Cluster"].tolist() #提取样本对应的簇

        # 10.然后我们再整理一下刚才得到的数据，得到差异基因热图中所有点对应的坐标和Z-score。然后就已经可以绘制差异基因热图了
        heatmap_values_df=heatmap_df.drop(columns=["Cluster"]) #删除"Cluster"列
        matrix_values=heatmap_values_df.fillna(0).values #把heatmap_values_df中的NaN填为0，然后把heatmap_values_df转换成numpy数组
        flat_values=matrix_values.ravel() #按行展平matrix_values，也就是把1,2,3\n4,5,6展平为1,2,3,4,5,6
        #现在我们就已经按行展平matrix_values了。但如果直接把flat_values返回给前端，前端是不知道flat_values中的某元素在matrix_values中是第几行第几列的。所以接下来我们把flat_values中的某元素在matrix_values中是第几行第几列也返回给前端
        #假设matrix_values有1031个样本、30个基因
        #请想象一个1031行、30列的矩阵，把它按行展平后，第一行第一列应为(0,0)，第一行最后一列应为(0,29)，第二行第一列应为(1,0)，第二行最后一列应为(1,29)，以此类推
        #也就是说我们要生成并返回的是[[0,0,某元素],[0,1,某元素],...,[0,29,某元素],[1,0,某元素],[1,1,某元素],...[1030,0,某元素],[1030,1,某元素],...,[1030,29,某元素]]。事实上，如果我们真的把这东西返回给前端，前端直接把它传给echarts就能绘制出热图了，而不需要对它做额外的处理
        #也就是说首先我们要生成[0,0,0,...,1,1,1,...,1030,1030,1030,...]和[0,1,2,...,29,0,1,2,...,29,...]
        n_rows,n_cols=matrix_values.shape #获取matrix_values的行数和列数。于是此时n_rows为1031，n_cols为30
        xs=np.repeat(np.arange(n_rows),n_cols) #np.arange(1031)会生成[0,1,2,...,1030]这个numpy数组，np.repeat会把每个元素重复30次，最终变成[0,0,0,...,1,1,1,...,1030,1030,1030,...]，长度是1031*30==295320 #给它命名为xs是因为在差异基因热图中该数组对应的是x轴
        ys=np.tile(np.arange(n_cols),n_rows) #np.arange(30)会生成[0,1,2,...,29]这个numpy数组，np.tile会把整个数组平铺1031次，最终变成[0,1,2,...,29,0,1,2,...,29,...]，长度是30*1031==295320
        heatmap_matrix=np.column_stack([xs,ys,flat_values]).tolist() #首先把xs、ys、flat_values放进列表里，同时传入np.column_stack，于是np.column_stack可以将这三个一维数组竖着拼成一个295320*3的矩阵，最后把它转换成列表，就能成功得到我们想要的返回给前端的东西了

        return{
            "status": "success",
            "volcano_data": volcano_data, #每个簇的用来绘制火山图的数据
            "heatmap_data": {
                "samples": sorted_samples, #提取出来的样本名称，也就是差异基因热图的x轴数据
                "sample_labels": sorted_labels, #提取出来的样本对应的簇，用于画差异基因热图的分组颜色条
                "genes": heatmap_values_df.columns.tolist(), #挑出来的基因名称，也就是差异基因热图的y轴数据
                "values": heatmap_matrix #差异基因热图中所有点对应的坐标和Z-score
            }
        }
    except Exception as e:
        print(f"[差异分析错误] {str(e)}")
        raise HTTPException(status_code=400,detail=str(e))

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