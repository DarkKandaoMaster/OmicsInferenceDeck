"""运行分析，运行用户选择的聚类算法。

本文件读取 upload.py 保存的组学数据，根据前端传来的算法名称和参数加载算法，
执行聚类并生成每个样本的标签和特征矩阵。结果会保存为 cluster_result.parquet，
供 metrics.py、pred_cluster_scatter.py、survival.py、differential.py 等后续接口使用。
"""

import os
import io
import datetime
import pandas as pd
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from algorithms import load_algorithm
from routers.upload import OMICS_DATA_FILE, CLINICAL_DATA_FILE, load_frame_dict
import shutil
from cleanup import cleanup_temp_files
import itertools
import numpy as np
from scipy.io import loadmat
import pandas as pd
from lifelines.statistics import multivariate_logrank_test
from plots.base import PARAMETER_SEARCH_FILE, PARAMETER_SEARCH_META_FILE, empty_svg, plot_path, write_json
from plots.parameter_surface import render_svg as render_parameter_svg

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
            n_neighbors=request.n_neighbors,
            omics_path=file_path,
        )

        # 3. 运行算法，获取聚类结果
        # fit_predict 返回：
        #   labels       — 形状 (n_samples,) 的 numpy 数组，每个样本的簇标签
        #   embeddings   — 形状 (n_samples, n_features) 的 numpy 数组，用于后续评估和降维
        #   sample_names — 长度 n_samples 的列表，样本名称
        labels, embeddings, sample_names = algo_instance.fit_predict(data_dict)

        # 4. 将中间结果持久化到 cluster_result.parquet，供 /api/metrics 和 /api/plots/pred_cluster_scatter 读取
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
            "message": f"算法 {request.algorithm} 运行成功，请调用 /api/metrics 获取指标，并调用 /api/plots/pred_cluster_scatter 获取散点图",
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



"""自定义算法结果评估，导入用户自己的聚类结果并纳入统一评价流程。

本文件用于用户已经在外部完成聚类的情况。它接收用户上传的结果文件，检查样本是否
能和 upload.py 保存的组学数据、临床数据对应上，然后保存成和 /api/run 相同格式的
cluster_result.parquet。这样 metrics.py、pred_cluster_scatter.py 等后续接口可以继续使用。
"""

@router.post("/api/evaluate_custom")
async def evaluate_custom(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    print(f"\n[后端日志] 收到自定义结果评估请求，会话ID：{session_id}")
    temp_paths = []
    try:
        UPLOAD_PATH = os.path.join("upload", session_id)
        if not os.path.exists(UPLOAD_PATH):
            os.makedirs(UPLOAD_PATH)

        # 1. 保存上传的结果文件（临时）
        file_location = os.path.join(UPLOAD_PATH, file.filename)
        temp_paths.append(file_location)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. 解析文件（首列为样本名索引，次列为聚类标签，其余列为特征矩阵）
        try:
            df = pd.read_csv(file_location, index_col=0, header=0)
        except Exception:
            try:
                df = pd.read_excel(file_location, index_col=0, header=0)
            except Exception as e:
                raise ValueError(f"结果文件解析失败，请确保格式正确: {str(e)}")

        if df.shape[1] < 1:
            raise ValueError(
                "结果数据格式不符：除样本名称（索引列）外，"
                "至少应包含一列聚类标签。"
            )

        sample_names = df.index.astype(str).tolist()

        # 3. 与已上传的组学/临床数据取交集，过滤无效样本
        valid_samples = set(sample_names)

        omics_path = os.path.join(UPLOAD_PATH, OMICS_DATA_FILE)
        if os.path.exists(omics_path):
            omics_dict = load_frame_dict(omics_path)
            omics_samples = set()
            for o_df in omics_dict.values():
                if not omics_samples:
                    omics_samples = set(o_df.index.astype(str))
                else:
                    omics_samples &= set(o_df.index.astype(str))
            valid_samples &= omics_samples

        clinical_path = os.path.join(UPLOAD_PATH, CLINICAL_DATA_FILE)
        if os.path.exists(clinical_path):
            clinical_dict = load_frame_dict(clinical_path)
            clinical_df = list(clinical_dict.values())[0]
            valid_samples &= set(clinical_df.index.astype(str))

        lost_samples = len(sample_names) - len(valid_samples)
        if len(valid_samples) == 0:
            raise ValueError(
                "交集校验失败！结果数据中的病人在您上传的组学或临床数据中均未找到匹配。"
            )

        # 4. 过滤后提取标签和特征矩阵
        df_filtered = df[df.index.astype(str).isin(valid_samples)]
        filtered_sample_names = df_filtered.index.astype(str).tolist()
        labels = df_filtered.iloc[:, 0].values
        embeddings = df_filtered.iloc[:, 1:].values

        # 5. 持久化中间结果，供 /api/metrics 和 /api/plots/pred_cluster_scatter 读取（Parquet 格式）
        n_features = embeddings.shape[1]
        df_result = pd.DataFrame(
            embeddings,
            columns=[f"emb_{i}" for i in range(n_features)]
        )
        df_result.insert(0, "sample_name", filtered_sample_names)
        df_result.insert(1, "label", labels)
        result_path = os.path.join(UPLOAD_PATH, "cluster_result.parquet")
        df_result.to_parquet(result_path, index=False)

        # 清理临时结果文件
        cleanup_temp_files(temp_paths)

        # 6. 返回基础聚类信息（不含指标和散点图，由独立指标/绘图接口负责）
        return {
            "status": "success",
            "message": "自定义结果解析成功，请调用 /api/metrics 获取指标，并调用 /api/plots/pred_cluster_scatter 获取散点图",
            "server_time": datetime.datetime.now().isoformat(),
            "data": {
                "method": "Custom Evaluation",
                "n_samples": len(filtered_sample_names),
                "n_features": int(embeddings.shape[1]),
                "labels": [int(l) for l in labels],
                "cluster_counts": {int(k): int(v) for k, v in pd.Series(labels).value_counts().items()},
                "lost_samples": lost_samples,  # 因交集过滤而丢弃的样本数
            }
        }

    except Exception as e:
        cleanup_temp_files(temp_paths)
        print(f"[自定义评估错误] {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))



"""批量测试算法参数并记录参数效果。

本文件读取 upload.py 保存的组学数据和临床数据，对前端给出的参数组合逐一运行
聚类算法，并用临床生存信息计算每组参数的分数。结果会保存为 parameter_search
文件，供 plots.py 绘制参数敏感性图。
"""
class ParameterSearchRequest(BaseModel):
    session_id: str
    algorithm: str
    param_grid: dict[str, list]
    random_state: int = 42


@router.post("/api/parameter_search")
async def run_parameter_search(request: ParameterSearchRequest):
    try:
        omics_path = plot_path(request.session_id, OMICS_DATA_FILE)
        clinical_path = plot_path(request.session_id, CLINICAL_DATA_FILE)
        if not omics_path.exists():
            raise FileNotFoundError("omics_data.parquet not found.")
        if not clinical_path.exists():
            raise FileNotFoundError("clinical_data.parquet not found.")

        omics_dict = load_frame_dict(omics_path)
        clinical_dict = load_frame_dict(clinical_path)
        clinical_df = list(clinical_dict.values())[0].copy()
        clinical_df.index = clinical_df.index.astype(str)

        algo_class = load_algorithm(request.algorithm)
        param_names = list(request.param_grid.keys())
        param_values = list(request.param_grid.values())
        combinations = list(itertools.product(*param_values))

        records: list[dict] = []
        best_score = -1.0
        best_params: dict | None = None

        for combo in combinations:
            params = dict(zip(param_names, combo))
            params_with_seed = {**params, "random_state": request.random_state}
            try:
                algo_instance = algo_class(**params_with_seed, omics_path=str(omics_path))
                labels, _, sample_names = algo_instance.fit_predict(omics_dict)
                cluster_df = pd.DataFrame({"Cluster": labels}, index=[str(s) for s in sample_names])
                merged = clinical_df.join(cluster_df, how="inner")
                if merged.empty or merged["Cluster"].nunique() < 2:
                    score = 0.0
                else:
                    lr_results = multivariate_logrank_test(merged["OS.time"], merged["Cluster"], merged["OS"])
                    p_val = float(lr_results.p_value) if np.isfinite(lr_results.p_value) else 1.0
                    score = float(-np.log10(p_val + 1e-300))
            except Exception:
                score = 0.0

            record = {k: v for k, v in params.items()}
            record["score"] = score
            records.append(record)

            if score > best_score:
                best_score = score
                best_params = {k: v for k, v in params.items()}

        result_df = pd.DataFrame(records)
        result_path = plot_path(request.session_id, PARAMETER_SEARCH_FILE)
        result_df.to_parquet(result_path, index=False)

        meta = {"best_params": best_params or {}, "best_score": best_score, "param_names": param_names}
        write_json(plot_path(request.session_id, PARAMETER_SEARCH_META_FILE), meta)

        x_param = param_names[0] if param_names else ""
        y_param = param_names[1] if len(param_names) > 1 else None
        try:
            plot_svg = render_parameter_svg(str(result_path), x_param, y_param)
        except Exception as exc:
            plot_svg = empty_svg(f"Parameter plot failed: {exc}", "Parameter Sensitivity")

        return {
            "status": "success",
            "best_params": best_params or {},
            "best_score": best_score,
            "param_names": param_names,
            "x_param": x_param,
            "y_param": y_param or "",
            "plot_svg": plot_svg,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



"""从上传的 .mat 直接绘制参数敏感性图（薄适配层）。

本端点用于读取学长算法（默认 MLMOSC 格式：X/Y/score = 第 15/16/17 列）已固化好的
结果矩阵——自动取 .mat 中首个非 __ 变量为数据数组，挑出 X/Y/score 三列写入与
parameter_search 同名的 parquet，复用 plots.parameter_surface 渲染、复用
/api/plots/download 下载，无需重跑任何算法、也不依赖任何原始组学/临床文件。
列号/轴标签可配置以适配其它 .mat。
"""


@router.post("/api/parameter_search_mat")
async def run_parameter_search_mat(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    x_col: int = Form(15),       # 1-indexed
    score_col: int = Form(17),   # 1-indexed
    x_label: str = Form("gamma"),
    y_col: str = Form("16"),     # 1-indexed；留空则画 2D 曲线
    y_label: str = Form("delta"),
):
    try:
        # 提前校验 session_id 并准备会话目录（plot_path 内部会校验 session_id 合法性）
        result_path = plot_path(session_id, PARAMETER_SEARCH_FILE)
        result_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. 不落盘：直接用 BytesIO 把上传内容交给 scipy 读取，避免任何临时目录
        raw = await file.read()
        try:
            mat = loadmat(io.BytesIO(raw))
        except Exception as exc:
            raise ValueError(f"无法解析 .mat 文件：{exc}")

        # 自动取首个非 __ 变量作为数据数组（照搬学长 parameter_sensitivity.py 的取法）
        data_keys = [k for k in mat.keys() if not k.startswith("__")]
        if not data_keys:
            raise ValueError("在 .mat 中找不到可用的数据变量（仅含元信息）。")

        arr = np.asarray(mat[data_keys[0]])
        if arr.ndim != 2:
            raise ValueError(f"变量 '{data_keys[0]}' 不是二维矩阵（当前形状 {arr.shape}）。")

        n_cols = arr.shape[1]

        def pick_col(col_1indexed: int, name: str) -> np.ndarray:
            idx = col_1indexed - 1
            if idx < 0 or idx >= n_cols:
                raise ValueError(f"{name} 列号 {col_1indexed} 越界（矩阵共 {n_cols} 列）。")
            return np.asarray(arr[:, idx], dtype=float)

        # 2. 取出 X / score；Y 仅在填写时取（留空即画 2D）
        x = pick_col(x_col, "X")
        z = pick_col(score_col, "−log10(p) / score")

        y_col_str = (y_col or "").strip()
        has_y = y_col_str != ""
        if has_y:
            try:
                y_index = int(y_col_str)
            except ValueError:
                raise ValueError(f"Y 列号 '{y_col_str}' 不是有效整数。")
            y = pick_col(y_index, "Y")

        # 3. 组装为现有渲染器认识的 DataFrame（列 = 参数名 + 一个 score 列）
        if has_y:
            data = {x_label: x, y_label: y, "score": z}
        else:
            data = {x_label: x, "score": z}
        result_df = pd.DataFrame(data).dropna()
        if result_df.empty:
            raise ValueError("解析后没有有效数据行（指定列可能全为 NaN）。")

        # 刻意复用同名 parquet，让下载接口 parameter_surface 分支零改动直接可用
        result_df.to_parquet(result_path, index=False)

        # 4. 计算最优行（score 最大）
        z_valid = result_df["score"].to_numpy()
        best_idx = int(np.argmax(z_valid))
        best_score = float(z_valid[best_idx])
        if has_y:
            best_params = {
                x_label: float(result_df[x_label].iloc[best_idx]),
                y_label: float(result_df[y_label].iloc[best_idx]),
            }
            param_names = [x_label, y_label]
        else:
            best_params = {x_label: float(result_df[x_label].iloc[best_idx])}
            param_names = [x_label]

        meta = {"best_params": best_params, "best_score": best_score, "param_names": param_names}
        write_json(plot_path(session_id, PARAMETER_SEARCH_META_FILE), meta)

        # 5. 渲染 SVG（无 Y → 现有渲染器自动画 2D 曲线）
        eff_y = y_label if has_y else ""
        try:
            plot_svg = render_parameter_svg(str(result_path), x_label, eff_y or None)
        except Exception as exc:
            plot_svg = empty_svg(f"Parameter plot failed: {exc}", "Parameter Sensitivity")

        return {
            "status": "success",
            "best_params": best_params,
            "best_score": best_score,
            "param_names": param_names,
            "x_param": x_label,
            "y_param": eff_y,
            "plot_svg": plot_svg,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"参数敏感性分析失败：{e}")
