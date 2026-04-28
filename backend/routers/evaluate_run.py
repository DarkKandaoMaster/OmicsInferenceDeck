# =============================================================================
# 接口：自定义算法结果评估
# =============================================================================
import os
import shutil
import datetime
import pandas as pd
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from cleanup import cleanup_temp_files
from routers.upload import CLINICAL_DATA_FILE, OMICS_DATA_FILE, load_frame_dict

# 创建路由器实例
router = APIRouter()


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

        if df.shape[1] < 2:
            raise ValueError(
                "结果数据格式不符：除样本名称（索引列）外，"
                "至少应包含一列聚类标签和一列特征数据。"
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

        # 5. 持久化中间结果，供 /api/metrics 和 /api/plots/cluster_scatter 读取（Parquet 格式）
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
            "message": "自定义结果解析成功，请调用 /api/metrics 获取指标，并调用 /api/plots/cluster_scatter 获取散点图",
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
