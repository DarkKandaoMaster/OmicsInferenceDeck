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
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from typing import List

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
#"/api/run"的数据校验模型
class AnalysisRequest(BaseModel): #定义一个类，在这个类里声明几个变量，并且明确指定这几个变量的类型。以此实现确保输入数据类型符合该要求，如果不符合，FastAPI会自动拦截并返回422错误
    #这里的冒号使用的是Python的类型提示语法。 变量名: 类型 意思是声明一个名为 变量名 的变量，它的预期类型是 类型 
    #虽然在普通Python代码中类型提示通常只是像注释一样给人看的，但在pydantic.BaseModel中，冒号具有强制性，Pydantic库会读取冒号后面的类型，并像C语言那样执行强制类型转换和验证
    algorithm: str #用户选择的算法名称
    timestamp: str #请求发起时的时间戳
    filename: str #用户上传的使用UUID改名后的组学数据文件名
    #以下参数具有默认值，所以以下参数是可选参数，其他算法即便不传这些参数也不会报错
    #K-means算法
    n_clusters: int=3 #聚类簇数（K值），默认3
    random_state: int=42 #随机种子，默认42
    max_iter: int=300 #最大迭代次数，默认300，用于防止算法在无法收敛时陷入死循环
    #用户选择的降维算法
    reduction: str="PCA" #用户选择的降维算法，默认PCA

#"/api/survival_analysis"的数据校验模型
class SurvivalRequest(BaseModel):
    clinical_filename: str #用户上传的使用UUID改名后的临床数据文件名
    sample: list[str] #样本名称列表
    labels: list[int] #和样本名称列表一一对应的聚类标签列表

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

    #接下来我们打算：
    # 1.读取"/api/upload"已经处理好的组学数据文件
    # 2.根据用户选择的算法训练模型并获取聚类标签
    # 3.计算三个聚类评估指标
    # 4.对df使用PCA/t-SNE/UMAP降维
    # 5.返回结果

    try:
        # 1.读取"/api/upload"已经处理好的组学数据文件
        file_path=os.path.join("upload",request.filename) #"/api/upload"已经处理好的组学数据文件的所在路径
        if not os.path.exists(file_path): #检查该路径是否存在
            raise FileNotFoundError(f"找不到文件: {request.filename}")
        df=pd.read_csv(file_path,header=0,index_col=0,sep=',') #因为"/api/upload"已经处理好文件了，所以这里可以直接这么读取输入数据
        print(f"[算法日志] 数据加载成功，形状为: {df.shape}")

        # 2.根据用户选择的算法训练模型并获取聚类标签
        model=None
        if request.algorithm=="K-means": #如果用户选择了K-means算法
            #初始化K-means模型，同时将前端传来的用户自定义的参数传入模型
            model=KMeans(
                n_clusters=request.n_clusters,
                random_state=seed,
                max_iter=request.max_iter
            )
        else: #如果用户选择了其他算法
            raise ValueError("选择了未实现的算法")
        labels=model.fit_predict(df) #按照用户设置的参数，使用df这个输入数据，不断地训练模型。训练结束后，返回最后一次训练结果

        # 3.计算三个聚类评估指标：轮廓系数、CH指数、DB指数，它们是可以用来给任何聚类算法打分的通用指标
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
        # 4.为了能够画散点图，我们需要对df使用PCA/t-SNE/UMAP降维。PCA/t-SNE/UMAP搞定散点图中的x、y坐标，需要评估的算法搞定散点图中点对应的簇
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
# 接口：处理用户上传组学和临床数据的接口
# =============================================================================
@app.post("/api/upload")
async def upload_file( files:List[UploadFile]=File(...) , data_format:str=Form(...) , file_type:str=Form("omics") ): #Files(...)表示该字段为必填的文件对象；Form(...)表示该字段为必填的表单对象。前端传过来的东西必须包含这两个对象 #file_type参数标记用户上传的是组学数据还是临床数据，默认是组学
    print(f"\n[后端日志] 收到文件上传请求，文件数量: {len(files)}") #在控制台打印日志
    print(f"[后端日志] 用户指定的数据格式: {data_format}")

    UPLOAD_PATH="upload" #用户上传文件的保存目录
    if not os.path.exists(UPLOAD_PATH): #如果目录不存在
        os.makedirs(UPLOAD_PATH) #则创建该目录

    #接下来我们打算：
    # 1.把各个文件都保存到本地
    # 2.根据用户选择的数据格式读取各个文件
    # 3.把读取到的各个文件合并成一个文件
    # 4.检查一下合并后的文件内容合不合规
    # 5.把合并后的文件保存到本地
    # 6.删除用户上传的各个文件
    # 7.返回结果

    dataframes=[] #我们希望把读取到并且处理好的各个文件都临时存放进这个列表，以便后续使用pd.concat合并
    temp_file_paths=[] #记录用户上传的各个文件的路径，以便后续删除这些文件
    try:
        for file in files: #遍历用户上传的每一个文件
            temp_filename=f"temp_{uuid.uuid4()}.csv" #使用uuid将用户上传的各个文件改个名，这样能防止两个用户同时上传同名文件导致覆盖，以及防止用户上传文件的名称不规范【【【【【这里的后缀名是不是无所谓的？推荐我把后缀名删除吗？
            file_location=os.path.join(UPLOAD_PATH,temp_filename) #得到用户上传的各个文件的保存路径
            temp_file_paths.append(file_location) #记录用户上传的各个文件的路径，以便后续删除这些文件

            # 1.把用户上传的各个文件都保存到本地
            with open(file_location,"wb") as buffer: #将文件流写入本地磁盘【【【【【话说这两句代码到底是什么意思？ #将上传的文件流写入服务器本地磁盘 #使用 with 语句确保文件句柄在操作完成后自动关闭 #【【【【【这句代码是什么意思？这是标准的文件写入操作，把上传的文件流保存到本地？
                shutil.copyfileobj(file.file,buffer)

            # 2.根据用户选择的数据格式读取各个文件
            #因为用户可能会把文件后缀名改成.fea之类的，所以我们不检查文件后缀名，我们直接来读文件
            df_single=None
            #因为需要使用pd.read_csv或pd.read_excel来读文件，所以这里用一个字典read_params来存储其参数
            read_params={
                "sep": None, #分隔符，默认None，表示自动嗅探分隔符
                "engine": "python", #使用Python引擎，这样才能支持自动嗅探分隔符
                "header": 0, #指定表头行为第0行，表示有表头
                "index_col": 0 #指定索引列为第0列，表示有索引列
            }
            need_transpose=False #标记是否需要转置
            #接下来我们要根据用户选择的数据格式修改read_params和need_transpose
            if data_format=="row_sample_yes_yes": #如果前端传过来的data_format为"row_sample_yes_yes"
                # ,特征1,特征2,特征3,...
                # 病人1,11,12,13
                # 病人2,21,22,23
                # 病人3,31,32,33
                # ...
                pass #那么就什么都不用做
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
                read_params["header"]=None
                read_params["index_col"]=0
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
                need_transpose=True #标记一下需要转置
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
                read_params["header"]=None #不指定表头行，于是读取文件时pandas会自动生成表头行0,1,2,...
                read_params["index_col"]=0
                need_transpose=True
            elif data_format=="row_feature_no_no":
                # 11,21,31,...
                # 12,22,32
                # 13,23,33
                # ...
                read_params["header"]=None
                read_params["index_col"]=None
                need_transpose=True
            #接下来我们来读取各个文件
            try:
                #首先我们尝试用pd.read_csv读文件
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
                    raise ValueError(f"文件 {file.filename} 解析失败: {str(e_read)}")
            if need_transpose: #如果需要转置
                df_single=df_single.T
            #此时读取出来的df_single就很标准了，行代表病人，列代表特征。有表头行、有索引列
            dataframes.append(df_single) #把读取到并且处理好的各个文件都临时存放进这个列表，以便后续使用pd.concat合并

        # 3.循环结束，此时dataframes里面应该就已经存放好了读取到并且处理好的各个文件，所以我们来合并一下
        if not dataframes:
            raise ValueError("未上传有效文件")
        df=pd.concat(dataframes,axis=1,join='inner') #axis=1表示在每一行后面拼接，即按列拼接；join='inner'表示取索引的交集，即“如果病人名称有对不上的，那么取病人名称的交集”
        if df.empty:
            raise ValueError("合并后数据为空！请检查数据格式选项是否正确，以及所有文件的病人名称是否一致。")
        original_shape=df.shape #记录合并后的形状
        print(f"[后端日志] 数据合并完成，合并后的形状: {df.shape}")

        # 4.合并各个文件成功后，我们还需要来检查一下合并后的文件内容合不合规，有没有脏数据什么的
        try:
            # 如果文件被解析为只有索引而没有特征列（比如 README.md），df.shape[1] 会是 0    。如果读取了空文件或仅有索引，shape[1] 为 0。
            #检查数据列数，确保df至少包含一列数据，防止读到空文件或者【【【【【改一下
            if df.shape[1]<1:
                raise ValueError("未检测到有效的数据列。")
            #检查样本名称是否重复
            if df.index.has_duplicates:
                duplicated_samples=df.index[df.index.duplicated()].unique().tolist() #获取具体的重复样本名【【【【【改一下。等会儿等会儿，因为我可能使用的是转置后的数据，所以这里的提示信息可能不太准确
                raise ValueError(f"合并后发现重复样本名: {duplicated_samples}。")
            #检查特征名称是否重复
            if df.columns.has_duplicates:
                duplicated_features=df.columns[df.columns.duplicated()].unique().tolist()
                raise ValueError(f"合并后发现重复特征名: {duplicated_features}。请确保不同组学文件中的特征不重名。")
            #如果是组学数据，那么检查整个表格中是否有缺失值，确保矩阵是稠密的；并且检查整个表格中是否有非数字内容
            if file_type=="omics":
                if df.isnull().sum().sum()>0: #df.isnull().sum().sum()可以计算整个表格中空值的总数
                    raise ValueError("数据中包含缺失值。科研数据要求完整，请手动清理或补全数据。") #如果需要更友好的提示，可以把此处改为遍历找出具体是哪一行哪一列空了
                non_numeric_cols=df.select_dtypes(exclude=[np.number]).columns.tolist() #select_dtypes(exclude=[np.number])可以筛选出所有非数字类型的列【【【【【非数字类型的列具体是什么？
                if len(non_numeric_cols)>0:
                    raise ValueError(f"以下列包含非数字内容: {non_numeric_cols}。请确保除行列头外，所有单元格均为数字。")
            else: #如果是临床数据，那么检查OS、OS.time两列数据是否有缺失值、是否有非数字内容【【【【【此处待实现
                pass
            print(f"[后端日志] 数据校验全部通过！最终用于分析的形状: {df.shape}")

            # 5.接下来我们要把合并后的文件保存到本地
            final_filename=f"{uuid.uuid4()}.csv" #给合并后的文件起个名
            final_file_location=os.path.join(UPLOAD_PATH,final_filename) #得到合并后的文件的保存路径
            df.to_csv(final_file_location) #把合并后的文件保存到本地
            #此时保存下来的df就很标准了，行代表病人，列代表特征。有表头行、有索引列
            #保存下来的文件，分隔符使用的是英文逗号，因为to_csv()函数的默认分隔符就是英文逗号
            #这样一来，"/api/run"接口就可以直接使用pd.read_csv(file_path,header=0,index_col=0,sep=',')读取输入数据了

            # 6.删除用户上传的各个文件
            for path in temp_file_paths:
                if os.path.exists(path):
                    os.remove(path)

        except Exception as e:
            raise HTTPException(status_code=400,detail=f"数据格式错误: {str(e)}")
        return{
            "status": "success",
            "filename": final_filename, #合并后的文件名称
            "original_filename": " + ".join([f.filename for f in files]), #用户上传的各个文件的原始名称。用于前端界面展示【【【【【这句代码是什么意思？
            "filepath": final_file_location, #合并后的文件的路径
            "original_shape": original_shape, #文件原始形状
            "final_shape": df.shape, #最终用于分析的文件形状
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
# 接口：生存分析
# =============================================================================
@app.post("/api/survival_analysis")
async def run_survival_analysis(request: SurvivalRequest):
    print(f"\n[后端日志] 收到生存分析请求，处理文件: {request.clinical_filename}")

    #接下来我们打算：
    # 1.读取"/api/upload"已经处理好的临床数据文件，得到clinical_df
    # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_df
    # 3.把clinical_df和cluster_df合并起来
    # 4.计算Log-Rank P-value
    # 5.计算绘制生存曲线所需数据
    # 6.返回结果

    try:
        # 1.读取"/api/upload"已经处理好的临床数据文件
        clinical_path=os.path.join("upload",request.clinical_filename) #"/api/upload"已经处理好的组学数据文件的所在路径
        if not os.path.exists(clinical_path):
            raise FileNotFoundError("找不到临床数据文件")
        clinical_df=pd.read_csv(clinical_path,header=0,index_col=0,sep=',') #因为"/api/upload"已经处理好文件了，所以这里可以直接这么读取输入数据

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

        # 4.计算Log-Rank P-value
        #首先我们来检查合并后的文件有没有"OS"、"OS.time"两列
        if "OS" not in merged_df.columns or "OS.time" not in merged_df.columns:
            raise ValueError("临床数据必须包含 'OS' (生存状态，1=死亡，0=存活) 和 'OS.time' (生存时间) 两列。")
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
            censored_probs=kmf.survival_function_at_times(censored_times).values.tolist() #获取删失点对应的生存概率 #.survival_function_at_times()返回的是Series，需要用.values转换为numpy数组
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
            "n_samples": len(merged_df) #合并后的行数，即合并后的样本数量
        }
    except Exception as e:
        print(f"[生存分析错误] {str(e)}")
        raise HTTPException(status_code=400,detail=str(e))

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