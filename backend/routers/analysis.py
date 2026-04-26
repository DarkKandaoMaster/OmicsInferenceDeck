# =============================================================================
# 接口：聚类评估指标计算 + 降维可视化
# 上游：/api/run 或 /api/evaluate_custom（二者都会写入 cluster_result.joblib）
# =============================================================================
import os
import json
import subprocess
import datetime
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 创建路由器实例
router = APIRouter()


def compute_r_metrics(parquet_path: str) -> dict:
    """通过 R 的 clusterCrit 包计算 Dunn / Xie-Beni / S_Dbw 指标。

    参数:
        parquet_path: cluster_result.parquet 文件路径
    返回:
        {"dunn": float, "xb": float, "s_dbw": float}，计算失败时各值为 -1
    """
    r_script = os.path.join(os.path.dirname(__file__),"analysis.R")
    r_script = os.path.abspath(r_script)

    # 防御：如果 R 脚本不存在，直接返回 -1
    if not os.path.exists(r_script):
        print(f"[R指标] 脚本不存在: {r_script}")
        return {"dunn": -1, "xb": -1, "s_dbw": -1}

    try:
        # 直接将 Parquet 路径传给 R，由 R 端读取
        result = subprocess.run(
            ["Rscript", r_script, parquet_path],
            capture_output=True, text=True, encoding="utf-8", timeout=3600 #如果超出3600秒，那么强行停止（开发阶段用）
        )

        if result.returncode != 0:
            print(f"[R指标] Rscript 错误: stderr={result.stderr.strip()}")
            return {"dunn": -1, "xb": -1, "s_dbw": -1}

        r_output = json.loads(result.stdout.strip())

        if "error" in r_output:
            print(f"[R指标] R 运行错误: {r_output['error']}")
            return {"dunn": -1, "xb": -1, "s_dbw": -1}

        return {
            "dunn":   r_output.get("dunn", -1),
            "xb":     r_output.get("xb", -1),
            "s_dbw":  r_output.get("s_dbw", -1),
        }

    except Exception as e:
        print(f"[R指标] 调用失败: {e}")
        return {"dunn": -1, "xb": -1, "s_dbw": -1}


class AnalysisRequest(BaseModel):
    session_id: str           # 会话 ID
    reduction: str = "PCA"    # 降维算法：PCA / t-SNE / UMAP
    random_state: int = 42    # 随机种子，-1 表示不固定


@router.post("/api/analysis")
async def analysis(request: AnalysisRequest):
    seed = request.random_state if request.random_state != -1 else None

    try:
        # 1. 读取上游写入的聚类中间结果（Parquet 格式）
        result_path = os.path.join("upload", request.session_id, "cluster_result.parquet")
        if not os.path.exists(result_path):
            raise FileNotFoundError(
                "找不到聚类结果文件，请先调用 /api/run 或 /api/evaluate_custom"
            )
        df_result = pd.read_parquet(result_path)
        sample_names = df_result["sample_name"].tolist()
        labels = df_result["label"].values
        emb_cols = [c for c in df_result.columns if c.startswith("emb_")]
        embeddings = df_result[emb_cols].values
        method = "Unknown" #原本这里是存放算法名称的，但是我在重构时把它删了
        metrics_scores = {} #存放计算出的数学指标

        # 2. 计算聚类评估指标# 3.计算三个聚类评估指标：轮廓系数、CH指数、DB指数，它们是可以用来给任何聚类算法打分的通用指标
        # 只有簇数 >= 2 时，三个指标才有数学意义
        n_unique = len(np.unique(labels))
        if n_unique >= 2:
            metrics_scores = {
                # 轮廓系数：[-1, 1]，越接近 1 越好
                # 衡量"组内紧密、组间分离"的综合得分
                #轮廓系数。范围[-1,1]，越接近1表示分类效果越好。衡量一个样本“离自己组的人有多近”、“离隔壁组的人有多远”
                "silhouette": round(float(silhouette_score(embeddings, labels)), 4), #将s_score强制类型转换float，然后四舍五入保留小数点后4位
                # CH 指数：[0, +∞)，越大越好
                # 衡量簇内紧密度与簇间分离度的比值
                #CH指数。范围[0,+∞)，值越大表示分类效果越好。衡量簇内紧密度与簇间分离度的比值，简单来说就是它希望“组内越紧密越好”、“组间离得越远越好”
                "calinski":   round(float(calinski_harabasz_score(embeddings, labels)), 4),
                # DB 指数：[0, +∞)，越小越好
                # 衡量簇之间的重叠程度
                #DB指数。范围[0,+∞)，值越小表示分类效果越好。衡量簇之间的重叠程度，如果这个指标很高，说明不同组混在一起了，分得不清楚
                "davies":     round(float(davies_bouldin_score(embeddings, labels)), 4),
            }
            # 【新增】调用 R 的 clusterCrit 计算 Dunn / Xie-Beni / S_Dbw
            r_metrics = compute_r_metrics(result_path)
            for key in ("dunn", "xb", "s_dbw"):
                val = r_metrics[key]
                metrics_scores[key] = None if isinstance(val, float) and np.isnan(val) else val

        else: #如果K<2，那么这些指标都无法计算，所以我们把这些指标都赋值为-1
            metrics_scores = {"silhouette": -1, "calinski": -1, "davies": -1, "dunn": -1, "xb": -1, "s_dbw": -1}

        #于是我们就计算出来那三个聚类评估指标了。但是它们不太直观，所以我们来另外计算一个散点图。如果聚类效果确实很好（样本确实分得很开），那么通常指标会很好、散点图也会分得很开，两者趋势是一致的
        # 4.为了能够画散点图，我们需要对df使用PCA/t-SNE/UMAP降维。PCA/t-SNE/UMAP搞定散点图中的x、y坐标，需要评估的算法搞定散点图中点对应的簇
        # 3. 降维，获取散点图坐标
        coords=None #用来存放降维后的结果
        if request.reduction == "PCA":
            # PCA：线性降维，速度最快，适合初步探索
            # 第 0 列 = PC1（方差最大方向），第 1 列 = PC2（方差第二大方向）
            #初始化PCA模型，指定降维到2维（x轴和y轴）；对df进行降维，返回一个形状为(样本数量,2)的numpy数组。其中第0列表示第一主成分（PC1），这是数据差异最大、最能区分样本的方向；第1列表示第二主成分（PC2），这是数据差异第二大的方向
            coords = PCA(n_components=2, random_state=seed).fit_transform(embeddings)
        elif request.reduction == "t-SNE":
            # t-SNE：非线性降维，擅长揭示局部簇结构，但不保留全局距离
            coords = TSNE(n_components=2, random_state=seed).fit_transform(embeddings)
        else: #如果用户选择了"UMAP"，或者选择了未知的降维算法，那么默认使用UMAP
            # UMAP：兼顾局部与全局结构，速度比 t-SNE 快
            coords = umap.UMAP(n_components=2, random_state=seed).fit_transform(embeddings)

        # 4. 组装散点图数据，每个样本一条记录
        #初始化一个列表，用来存放每个样本对应的信息，以便前端画散点图。在前端的散点图中，每个样本对应一个点
        plot_data = [
            {
                "name":    str(sample_names[i]), #样本名称
                "x":       float(coords[i, 0]), #降维后的第一主成分，作为散点图中的x轴坐标
                "y":       float(coords[i, 1]), #降维后的第二主成分，作为散点图中的y轴坐标
                "cluster": int(labels[i]), #该样本所属的簇标签
            }
            for i in range(len(sample_names))
        ]

        return {
            "status": "success",
            "message": f"评估完成（方法：{method}，降维：{request.reduction}）",
            "server_time": datetime.datetime.now().isoformat(),
            "data": {
                "method":   method,
                "metrics":  metrics_scores,
                "plot_data": plot_data,
            }
        }

    except Exception as e:
        print(f"[可视化错误] {str(e)}")
        raise HTTPException(status_code=400, detail=f"评估/降维失败: {str(e)}")
