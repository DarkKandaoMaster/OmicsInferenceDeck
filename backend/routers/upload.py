"""处理用户上传的组学数据和临床数据。

本文件负责接收前端上传的文件，按用户选择的数据格式读成 pandas DataFrame，
再把清洗后的数据保存到当前 session 的 upload 目录中。其他路由会继续读取这里
保存的 omics_data.parquet、clinical_data.parquet 以及对应的 JSON 元数据。
"""

import os
import json
import shutil
import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from typing import List
from cleanup import cleanup_temp_files
from pathlib import Path
from typing import Any

OMICS_DATA_FILE = "omics_data.parquet"
CLINICAL_DATA_FILE = "clinical_data.parquet"
OMICS_META_FILE = "omics_data.json"
CLINICAL_META_FILE = "clinical_data.json"


def input_data_files(file_type: str) -> tuple[str, str]:
    if file_type == "omics":
        return OMICS_DATA_FILE, OMICS_META_FILE
    return CLINICAL_DATA_FILE, CLINICAL_META_FILE


def _metadata_path(parquet_path: str | Path) -> Path:
    path = Path(parquet_path)
    return path.with_suffix(".json")


def save_frame_dict(data: dict[str, pd.DataFrame], parquet_path: str | Path, metadata_path: str | Path | None = None) -> None:
    parquet_path = Path(parquet_path)
    metadata_path = Path(metadata_path) if metadata_path is not None else _metadata_path(parquet_path)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    stored_frames: list[pd.DataFrame] = []
    metadata: dict[str, Any] = {"version": 1, "frames": []}
    for frame_index, (key, df) in enumerate(data.items()):
        stored = df.copy()
        columns = []
        for column_index, column_name in enumerate(stored.columns):
            storage_name = f"frame_{frame_index}__col_{column_index}"
            columns.append({"storage_name": storage_name, "name": str(column_name)})
        stored.columns = [column["storage_name"] for column in columns]
        stored_frames.append(stored)
        metadata["frames"].append({"key": str(key), "columns": columns})

    combined = pd.concat(stored_frames, axis=1, join="outer") if stored_frames else pd.DataFrame()
    combined.index.name = combined.index.name or "sample_name"
    combined.to_parquet(parquet_path, index=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def load_frame_dict(parquet_path: str | Path, metadata_path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    parquet_path = Path(parquet_path)
    metadata_path = Path(metadata_path) if metadata_path is not None else _metadata_path(parquet_path)
    combined = pd.read_parquet(parquet_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    data: dict[str, pd.DataFrame] = {}
    for frame_meta in metadata.get("frames", []):
        columns = frame_meta.get("columns", [])
        storage_names = [column["storage_name"] for column in columns]
        display_names = [column["name"] for column in columns]
        frame = combined.loc[:, storage_names].copy()
        frame.columns = display_names
        data[str(frame_meta["key"])] = frame.dropna(how="all")
    return data




# 创建路由器实例
router=APIRouter()

#@router.post是一个装饰器，它的作用是将下面的upload_file函数注册到Web服务器的路由表中，当用户发送POST请求到"/api/upload"这个网址时，服务器会自动调用下面的upload_file函数来处理，同时FastAPI会自动读取HTTP请求体中的数据，并将其传给upload_file函数中的形参，实现接收输入数据
#async可以定义异步函数，允许在进行文件读写或等待模型推理时，服务器可以挂起当前任务去处理其他请求，提高并发吞吐量
@router.post("/api/upload")
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

            # 获取基础的组学类型，作为 data_dict 的键名
            if file_type == "omics":
                # 根据文件名(UUID)在映射字典中找类型，找不到默认Unknown
                base_type = mapping.get(file.filename, "Unknown")

                # 修改特征名称（列名）！格式：特征名称_组学【【【【【我当初为什么会把特征名称改名的来着？？不改名然后直接用字典的键来区分不是更好？
                df_single.columns = [f"{col}_{base_type}" for col in df_single.columns]

                # 同组学类型自动合并机制
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

            data_dict = {key: df.loc[df_concat.index].copy() for key, df in data_dict.items()} #upload.py 保存前会把各组学数据裁剪到已校验过的交集样本

            # 保存输入数据：DataFrame 内容写入 parquet，字典结构等元数据写入 JSON。
            parquet_filename, metadata_filename = input_data_files(file_type)
            final_file_location=os.path.join(UPLOAD_PATH, parquet_filename)
            final_metadata_location=os.path.join(UPLOAD_PATH, metadata_filename)
            legacy_joblib_location=os.path.join(UPLOAD_PATH, "omics_data.joblib" if file_type=="omics" else "clinical_data.joblib")
            for existing_path in (final_file_location, final_metadata_location, legacy_joblib_location):
                if os.path.exists(existing_path):
                    os.remove(existing_path)
            save_frame_dict(data_dict, final_file_location, final_metadata_location)
            # # 5.接下来我们要把合并后的文件保存到本地
            # final_filename=f"{uuid.uuid4()}.csv" #给合并后的文件起个名
            # final_file_location=os.path.join(UPLOAD_PATH,final_filename) #得到合并后的文件的保存路径
            # df.to_csv(final_file_location) #把合并后的文件保存到本地
            # #此时保存下来的df就很标准了，行代表病人，列代表特征。有表头行、有索引列
            # #保存下来的文件，分隔符使用的是英文逗号，因为to_csv()函数的默认分隔符就是英文逗号
            # #这样一来，"/api/run"接口就可以直接使用pd.read_csv(file_path,header=0,index_col=0,sep=',')读取输入数据了

            # 6.删除用户上传的各个文件
            cleanup_temp_files(temp_file_paths)

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
        cleanup_temp_files(temp_file_paths) #删除用户上传的各个文件
        print(f"[后端日志] 校验不通过，文件已删除: {str(he)}")
        raise he #直接抛出错误给前端
    except Exception as e: #说明读取文件失败，或者其他什么错误
        cleanup_temp_files(temp_file_paths) #删除用户上传的各个文件
        print(f"[后端日志] 严重错误，文件已删除: {str(e)}")
        raise HTTPException(status_code=500,detail=f"服务器内部错误: {str(e)}") #抛出错误给前端
