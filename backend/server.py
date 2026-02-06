import uvicorn
from fastapi import FastAPI,HTTPException,File,UploadFile,Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import datetime
import shutil
import os
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import uuid
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import random
import torch

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
    version="1.0.0" #设置版本号
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
# 数据校验模型定义
# =============================================================================
#定义请求体的数据校验模型
class AnalysisRequest(BaseModel): #定义一个类，在这个类里声明几个变量，并且明确指定这几个变量的类型。以此实现确保输入数据类型符合该要求，如果不符合，FastAPI会自动拦截并返回422错误
    #这里的冒号使用的是Python的类型提示语法。 变量名: 类型 意思是声明一个名为 变量名 的变量，它的预期类型是 类型 
    #虽然在普通Python代码中类型提示通常只是像注释一样给人看的，但在pydantic.BaseModel中，冒号具有强制性，Pydantic库会读取冒号后面的类型，并像C语言那样执行强制类型转换和验证
    algorithm: str #用户选择的算法名称
    timestamp: str #请求发起时的时间戳
    filename: str #用户上传的文件名
    #以下参数具有默认值，所以以下参数是可选参数，其他算法即便不传这些参数也不会报错
    #K-means算法
    n_clusters: int=3 #聚类簇数（K值），默认3
    random_state: int=42 #随机种子，默认42
    max_iter: int=300 #最大迭代次数，默认300，用于防止算法在无法收敛时陷入死循环
    #用户选择的降维算法
    reduction: str="UMAP" #用户选择的降维算法，默认UMAP

# =============================================================================
# 接口：运行分析
# =============================================================================
#@app.post是一个装饰器，它的作用是将下面的run_analysis函数注册到Web服务器的路由表中，当用户发送POST请求到“/api/run”这个网址时，服务器会自动调用下面的run_analysis函数来处理，同时FastAPI会自动读取HTTP请求体中的数据，并将其传给下面的request参数，实现接收输入数据
#async可以定义异步函数，允许在进行文件读写或等待模型推理时，服务器可以挂起当前任务去处理其他请求，提高并发吞吐量
@app.post("/api/run")
async def run_analysis(request: AnalysisRequest): #指定record的类型为AnalysisRequest，就是我们刚才定义的那个类，如果前端传来的数据类型不匹配，FastAPI会自动拦截并返回422错误
    print(f"\n[后端日志] 收到分析请求:") #在控制台打印日志（实际生产环境中建议使用logging模块替代print）
    print(f"   - 用户选择的算法名称: {request.algorithm}")
    print(f"   - 时间戳: {request.timestamp}")
    print(f"   - 用户上传的文件名: {request.filename}")
    print(f"   - 用户选择的降维算法: {request.reduction}")
    print(f"   - 参数: K={request.n_clusters}, Seed={request.random_state}, Iter={request.max_iter}")

    #设置全局随机种子。虽然下面这几句代码是写在函数里的，但它们生效的范围是全局。所以虽然在当前开发阶段这么写是完全可取的，但如果我以后要构建一个高并发的商业级服务器，这么写就不可取了
    seed=request.random_state if request.random_state!=-1 else None #如果用户传的是-1，变量设为None；否则设为用户传来的整数
    random.seed(seed) # 设置Python原生random库的种子
    np.random.seed(seed) #设置NumPy的随机种子
    seed_for_torch=request.random_state if request.random_state!=-1 else random.randint(0,2**32-1) #pytorch比较特殊，不能直接把None作为种子，所以我们随机生成一个整数作为种子
    torch.manual_seed(seed_for_torch) #设置CPU生成随机数的种子
    torch.cuda.manual_seed(seed_for_torch) #为当前GPU设置随机种子
    torch.cuda.manual_seed_all(seed_for_torch) #为所有GPU设置随机种子

    mock_result_data={} #初始化结果字典，这个就是函数要返回的东西之一

    # -------------------------------------------------------------------------
    # 算法：K-means
    # -------------------------------------------------------------------------
    if request.algorithm=="K-means":
        try:
            file_path=os.path.join("upload",request.filename) #需要处理的文件的所在路径
            if not os.path.exists(file_path): #检查该路径是否存在（检查文件是否存在）
                raise FileNotFoundError(f"找不到文件: {request.filename}")

            df=pd.read_csv(file_path,header=0,index_col=0,sep=',') #因为"/api/upload"已经处理好文件了，所以这里可以直接这么读取输入数据
            print(f"[算法日志] 数据加载成功，形状为: {df.shape}")

            #初始化K-means模型，同时将前端传来的用户自定义的参数传入模型【【【或许以后可以在这里写个if，最小改动地使用其他算法？】】】
            kmeans=KMeans(
                n_clusters=request.n_clusters,
                random_state=seed,
                max_iter=request.max_iter
            )
            labels=kmeans.fit_predict(df) #按照用户设置的参数，使用df这个输入数据，不断地训练模型。训练结束后，返回最后一次训练结果

            #计算三个聚类评估指标：轮廓系数、CH指数、DB指数，它们是可以用来给任何聚类算法打分的通用指标
            metrics_scores={} #初始化一个字典，用来存放这三个指标
            if request.n_clusters>=2: #只有当簇数量大于等于2时，聚类评估指标才有数学意义
                s_score=silhouette_score(df,labels) #轮廓系数。范围[-1,1]，越接近1表示分类效果越好。衡量一个样本“离自己组的人有多近”、“离隔壁组的人有多远”
                ch_score=calinski_harabasz_score(df,labels) #CH指数。范围[0,+∞)，值越大表示分类效果越好。衡量簇内紧密度与簇间分离度的比值，简单来说就是它希望“组内越紧密越好”、“组间离得越远越好”
                db_score=davies_bouldin_score(df,labels) #DB指数。范围[0,+∞)，值越小表示分类效果越好。衡量簇之间的重叠程度，如果这个指标很高，说明不同组混在一起了，分得不清楚
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
            #为了能够画散点图，我们需要对df使用PCA/t-SNE/UMAP降维。PCA/t-SNE/UMAP搞定散点图中的x、y坐标，需要评估的算法搞定散点图中点对应的簇
            coords=None #用来存放降维后的结果
            if request.reduction=="PCA":
                coords=PCA(n_components=2,random_state=seed)   .fit_transform(df) #初始化PCA模型，指定降维到2维（x轴和y轴）；对df进行降维，返回一个形状为(样本数量,2)的numpy数组。其中第0列表示第一主成分（PC1），这是数据差异最大、最能区分样本的方向；第1列表示第二主成分（PC2），这是数据差异第二大的方向
            elif request.reduction=="t-SNE":
                coords=TSNE(n_components=2,random_state=seed)   .fit_transform(df)
            elif request.reduction=="UMAP":
                coords=umap.UMAP(n_components=2,random_state=seed)   .fit_transform(df)
            else: #兜底逻辑：如果用户选择了未知的降维算法，那么默认使用UMAP
                coords=umap.UMAP(n_components=2,random_state=seed)   .fit_transform(df)
            plot_data=[] #初始化一个列表，用来存放每个样本对应的信息，以便前端画散点图。在前端的散点图中，每个样本对应一个点
            for i in range(len(df)):
                plot_data.append({
                    "name": df.index[i], #样本名称
                    "x": float(coords[i,0]), #降维后的第一主成分，作为散点图中的x轴坐标
                    "y": float(coords[i,1]), #降维后的第二主成分，作为散点图中的y轴坐标
                    "cluster": int(labels[i]) #该样本所属的簇标签
                })

            #为结果字典赋值
            mock_result_data={
                "method": "K-means (Real Run)",
                "n_samples": df.shape[0], #样本总数
                "n_features": df.shape[1], #特征数量
                "inertia": float(kmeans.inertia_), #簇内误差平方和，评估聚类效果的指标，该值越小，表示簇内样本越紧密
                "labels": labels.tolist(), #将numpy数组转换为Python列表，不然numpy数组无法直接序列化为JSON
                "cluster_counts": pd.Series(labels).value_counts().to_dict(), #统计每个类别（簇）的样本数量
                "metrics": metrics_scores, #我们刚才计算出来的聚类评估指标
                "plot_data": plot_data #存放每个样本对应的信息的那个列表
            }
            print("[算法日志] K-means 计算完成") #在控制台打印日志

        except Exception as e: #处理用户参数设置不合理，或者上传了一个非常大的CSV文件并且上传时硬盘存得下但处理时硬盘存不下，等情况
            print(f"[算法错误] {str(e)}")
            return{
                "status": "error", 
                "message": f"算法运行失败: {str(e)}",
                "server_time": datetime.datetime.now().isoformat()
            }

    # -------------------------------------------------------------------------
    # 算法：PIntMF (模拟实现)
    # -------------------------------------------------------------------------
    elif request.algorithm=="PIntMF":
        # 实际开发中，此处应调用 R 语言脚本 (rpy2) 或相应的 Python 实现。
        pass

    # -------------------------------------------------------------------------
    # 算法：Subtype-GAN (模拟实现)
    # -------------------------------------------------------------------------
    elif request.algorithm=="Subtype-GAN":
        pass
    else: #如果用户选择了其他算法
        mock_result_data={
            "info": f"算法 {request.algorithm} 的接口尚未完全实现",
            "status": "pending"
        }

    #构建HTTP响应
    #下面这个字典就是要返回给前端的东西
    response={
        "status": "success",
        "message": f"算法 {request.algorithm} 调用成功！",
        "server_time": datetime.datetime.now().isoformat(), #当前时间戳，格式为ISO 8601
        "data": mock_result_data #我们刚才操作的结果字典
    }
    print(f"[后端日志] 返回结果: {response['status']}")
    return response #FastAPI会自动将这个字典序列化成JSON字符串，然后通过网络发送给前端

# =============================================================================
# 接口：处理用户上传文件的接口
# =============================================================================
@app.post("/api/upload")
async def upload_file( file:UploadFile=File(...) , data_format:str=Form(...) ): #File(...)表示该字段为必填的文件对象；Form(...)表示该字段为必填的表单对象。前端传过来的东西必须包含这两个对象
    print(f"\n[后端日志] 收到文件上传请求: {file.filename}") #在控制台打印日志
    print(f"[后端日志] 用户指定的数据格式: {data_format}")

    UPLOAD_PATH="upload" #用户上传文件的保存目录
    if not os.path.exists(UPLOAD_PATH): #如果目录不存在，则创建该目录
        os.makedirs(UPLOAD_PATH)
    new_filename=f"{uuid.uuid4()}.csv" #用户上传文件的新名称。使用uuid将用户上传文件改个名，这样能防止两个用户同时上传同名文件导致覆盖，以及防止用户上传文件的名称不规范；将后缀名固定改为.csv，因为我们之后会把处理好的文件保存为CSV格式
    file_location=os.path.join(UPLOAD_PATH,new_filename) #用户上传文件的保存路径

    try:
        #将用户上传文件老老实实保存到本地
        #将上传的文件流写入服务器本地磁盘
        #使用 with 语句确保文件句柄在操作完成后自动关闭
        with open(file_location,"wb") as buffer: #【【【【【这句代码是什么意思？
            shutil.copyfileobj(file.file,buffer)
        print(f"[后端日志] 文件已保存至: {file_location}")

        #根据用户选择的数据格式读取文件
        df=None
        original_shape=(0,0) #用于记录文件原始形状
        try:
            #因为用户可能会把文件后缀名改成.fea之类的，所以我们不检查文件后缀名，我们直接来读文件
            #因为需要使用pd.read_csv或pd.read_excel来读文件，所以这里用一个字典来存储其参数
            read_params={
                "sep": None, #分隔符，默认None，表示自动嗅探分隔符
                "engine": "python", #使用Python引擎，这样才能支持自动嗅探分隔符
                "header": 0, #指定表头行为第0行，表示有表头
                "index_col": 0 #指定索引列为第0列，表示有索引列
            }
            need_transpose=False #标记是否需要转置
            if data_format=="row_feat_col_sample": #如果前端传过来的data_format为"row_feat_col_sample"
                #,特征1,特征2
                #样本1,10,20
                #样本2,30,40
                pass #那么就什么都不用做
            elif data_format=="row_sample_col_feat":
                #,样本1,样本2
                #特征1,10,30
                #特征2,20,40
                need_transpose=True #标记一下需要转置
            elif data_format=="row_feat":
                #特征1,特征2
                #10,20
                #30,40
                read_params["index_col"]=None #不指定索引列，于是读取文件时pandas会自动生成索引列0,1,2,...
            elif data_format=="row_sample":
                #样本1,样本2
                #10,30
                #20,40
                read_params["index_col"]=None
                need_transpose=True
            elif data_format=="col_feat":
                #特征1,10,20
                #特征2,30,40
                read_params["header"]=None #不指定表头行，于是读取文件时pandas会自动生成表头行0,1,2,...
                read_params["index_col"]=0
                need_transpose=True
            elif data_format=="col_sample":
                #样本1,10,20
                #样本2,30,40
                read_params["header"]=None
                read_params["index_col"]=0
            elif data_format=="no_name_row_sample":
                #10,20
                #30,40
                read_params["header"]=None
                read_params["index_col"]=None
            elif data_format=="no_name_row_feat":
                #10,30
                #20,40
                read_params["header"]=None
                read_params["index_col"]=None
                need_transpose=True

            #读取文件
            try:
                #首先我们尝试用pd.read_csv读文件
                #**是Python的字典解包语法，可以把 字典键值对 拆解成 函数参数 
                #假设有一个函数需要两个参数：def hanshu(a,b)
                #普通调用方式：hanshu(a=1,b=2)
                #使用**的调用方式：hanshu(**{"a":1,"b":2})
                df=pd.read_csv(file_location,**read_params)
            except:
                #如果读取失败，那么尝试用pd.read_excel读文件。不过pd.read_excel不支持sep和engine参数，所以我们先来删除它们 #注意想要使用pd.read_excel的话需要先安装openpyxl库
                del read_params["sep"]
                del read_params["engine"]
                df=pd.read_excel(file_location,**read_params)
                #如果还是读取失败，那么程序会触发外层try的异常捕获机制，首先是被except Exception as e_read捕获，抛出ValueError；然后是被最外层的except Exception as e捕获，删除文件同时抛出HTTPException

            original_shape=df.shape #记录文件原始形状
            print(f"[后端日志] 文件原始形状: {original_shape}")
            if need_transpose: #如果需要转置
                df=df.T
                print(f"[后端日志] 数据已转置，当前形状: {df.shape}")
        except Exception as e_read:
             raise ValueError(f"文件解析失败，请检查格式选项是否正确。错误信息: {str(e_read)}")

        #此时读取出来的df就很标准了，有表头行有索引列，第一行为特征名称，第一列为样本名称
        #读取文件成功后，我们还需要来检查一下内容合不合规，看看有没有脏数据什么的
        try:
            # 如果文件被解析为只有索引而没有特征列（比如 README.md），df.shape[1] 会是 0    确保 DataFrame 。如果读取了空文件或仅有索引，shape[1] 为 0。
            #检查数据列数，确保df至少包含一列数据，防止读到空文件或者【【【【【改一下
            if df.shape[1]<1:
                raise ValueError("未检测到有效的数据列。请检查分隔符是否正确（当前仅支持逗号分隔），或文件是否包含特征数据。")

            #检查样本名称是否重复
            if df.index.has_duplicates:
                duplicated_samples=df.index[df.index.duplicated()].unique().tolist() #获取具体的重复样本名【【【【【改一下。等会儿等会儿，因为我可能使用的是转置后的数据，所以这里的提示信息可能不太准确
                raise ValueError(f"数据第一列（样本名称）发现重复值: {duplicated_samples}。请确保每个样本只有一行。")

            #检查特征名称是否重复
            if df.columns.has_duplicates:
                duplicated_features=df.columns[df.columns.duplicated()].unique().tolist()
                raise ValueError(f"数据第一行（特征名称）发现重复值: {duplicated_features}。请确保特征名称不重复。")

            #检查是否有缺失值（空值），确保矩阵是稠密的
            if df.isnull().sum().sum()>0: #df.isnull().sum().sum()可以计算整个表格中空值的总数
                raise ValueError("数据中包含缺失值（空值）。科研数据要求完整，请手动清理或补全数据。") #如果需要更友好的提示，可以把此处改为遍历找出具体是哪一行哪一列空了

            # 我们尝试将所有列转换为数字，如果某一列包含无法转换的字符（如字符串），Pandas会将该列类型识别为 object【【【【【改一下。这是什么意思？
            #检查内容是否全为数字（第一行、第一列除外）
            non_numeric_cols=df.select_dtypes(exclude=[np.number]).columns.tolist() #select_dtypes(exclude=[np.number])可以筛选出所有非数字类型的列【【【【【非数字类型的列是怎么个事？
            if len(non_numeric_cols)>0:
                raise ValueError(f"以下列包含非数值内容: {non_numeric_cols}。请确保除行列头外，所有单元格均为数字。")

            print(f"[后端日志] 数据校验全部通过！最终用于分析的形状: {df.shape}")

            df.to_csv(file_location) #将df保存到磁盘
            #此时保存下来的df就很标准了，有表头行有索引列，第一行为特征名称，第一列为样本名称
            #保存下来的文件，路径、文件名、后缀名和原文件（使用uuid改名后的文件）完全一样，也就是说保存下来的文件会覆盖原文件
            #保存下来的文件，分隔符使用的是英文逗号，因为to_csv()函数的默认分隔符就是英文逗号
            #这样一来，"/api/run"接口就可以直接使用pd.read_csv(file_path,header=0,index_col=0,sep=',')读取输入数据了。虽然确实有可能出现read_csv一个.xlsx文件这种情况，不过这不碍事
        except Exception as e:
            raise HTTPException(status_code=400,detail=f"数据格式错误: {str(e)}")

        return{
            "status": "success",
            "filename": new_filename, #用户上传文件的新名称
            "original_filename": file.filename, #用户上传文件的原始名称。用于前端界面展示
            "filepath": file_location,
            "original_shape": original_shape, #文件原始形状
            "final_shape": df.shape, #最终用于分析的文件形状
            "message": f"文件 {file.filename} 上传成功"
        }
    except HTTPException as he: #捕获到了我们刚才自己抛出的错误，说明虽然读取文件成功，但是文件内容不合规
        if os.path.exists(file_location):
            os.remove(file_location) #删除文件
        print(f"[后端日志] 校验不通过，文件已删除: {str(he)}")
        raise he #直接抛出错误给前端
    except Exception as e: #说明读取文件失败，或者其他什么错误
        if os.path.exists(file_location):
            os.remove(file_location) #删除文件
        print(f"[后端日志] 严重错误，文件已删除: {str(e)}")
        raise HTTPException(status_code=500,detail=f"服务器内部错误: {str(e)}") #抛出错误给前端

# =============================================================================
# 程序入口
# =============================================================================
if __name__=="__main__": #这是Python的标准入口判断。只有当这个文件被直接运行（而不是作为模块被导入）（即python server.py）时，下面的代码才会执行
    #启动Uvicorn服务器
    #我们刚才不是实例化了一个app对象嘛，现在我们将app作为参数传给Uvicorn服务器，于是当服务器收到请求时，可以找到并调用对应的有@app.post修饰的函数
    uvicorn.run(app,host="0.0.0.0",port=8000) #这句代码的意思就是让Uvicorn服务器加载app这个对象，并且在所有网卡（0.0.0.0）上监听 8000 端口，随时接收请求
    #host="0.0.0.0"对应底层Socket编程中的INADDR_ANY宏，意思是监听本机“所有”网卡接口。也就是说允许外部设备（如同一局域网下的其他电脑）访问本服务
    #一旦执行这句代码，主线程将进入一个无限循环，持续挂起以监听网络端口。也就是说这之后的代码都执行不了了，除非进程被信号终止
    #此时你还会发现 http://127.0.0.1:8000/docs 、 http://127.0.0.1:8000/redoc 可以打开。这是FastAPI框架自带的自动生成交互式API文档功能