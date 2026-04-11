# =============================================================================
# 接口：自定义算法结果评估
# =============================================================================
import os
import shutil
import datetime
import joblib
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from cleanup import cleanup_temp_files

# 创建路由器实例
router=APIRouter()

@router.post("/api/evaluate_custom")
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
        cleanup_temp_files(temp_paths)

        return {
            "status": "success",
            "message": "自定义结果评估成功！",
            "server_time": datetime.datetime.now().isoformat(),
            "data": mock_result_data
        }

    except Exception as e:
        cleanup_temp_files(temp_paths)
        print(f"[自定义评估错误] {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
