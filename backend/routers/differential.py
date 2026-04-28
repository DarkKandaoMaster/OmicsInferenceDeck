"""比较不同聚类之间的组学特征差异。

本文件读取 upload.py 保存的组学数据和 run.py 或 evaluate_run.py 生成的聚类结果，
对每个聚类做“该聚类 vs 其他聚类”的差异分析。它会保存火山图和热图所需的数据，
供 enrichment.py 继续做富集分析，也供 plots.py 重新绘图或下载。
"""

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from scipy import stats
from routers.upload import OMICS_DATA_FILE, load_frame_dict

from plots.base import (
    CLUSTER_RESULT_FILE,
    DIFFERENTIAL_HEATMAP_FILE,
    DIFFERENTIAL_META_FILE,
    DIFFERENTIAL_VOLCANO_FILE,
    empty_svg,
    plot_path,
    run_r_svg,
    write_json,
)
from plots.differential_volcano import render_svg as render_volcano_svg


router = APIRouter()


class DifferentialAnalysisRequest(BaseModel):
    session_id: str
    omics_type: str
    sample: list[str] | None = None
    labels: list[int] | None = None


def _load_omics_frame(session_id: str, omics_type: str) -> pd.DataFrame:
    omics_path = plot_path(session_id, OMICS_DATA_FILE)
    if not omics_path.exists():
        raise FileNotFoundError("omics_data.parquet not found. Please upload omics data first.")

    data_dict = load_frame_dict(omics_path)
    if omics_type == "All (Concatenated)":
        return pd.concat(list(data_dict.values()), axis=1, join="inner")
    if omics_type not in data_dict:
        raise ValueError(f"Omics type not found: {omics_type}")

    df = data_dict[omics_type].copy()
    suffix = f"_{omics_type}"
    df.columns = [str(col)[: -len(suffix)] if str(col).endswith(suffix) else str(col) for col in df.columns]
    return df


def _load_cluster_info(session_id: str) -> pd.DataFrame:
    cluster_path = plot_path(session_id, CLUSTER_RESULT_FILE)
    if not cluster_path.exists():
        raise FileNotFoundError("cluster_result.parquet not found. Please run clustering first.")
    cluster_df = pd.read_parquet(cluster_path)[["sample_name", "label"]].copy()
    cluster_df["sample_name"] = cluster_df["sample_name"].astype(str)
    cluster_df = cluster_df.rename(columns={"label": "Cluster"}).set_index("sample_name")
    return cluster_df


@router.post("/api/differential_analysis")
async def run_differential_analysis(request: DifferentialAnalysisRequest):
    try:
        df = _load_omics_frame(request.session_id, request.omics_type)
        df.index = df.index.astype(str)
        cluster_info = _load_cluster_info(request.session_id)

        merged_df = df.join(cluster_info, how="inner")
        if merged_df.empty:
            raise ValueError("No matching samples between omics data and clustering result.")

        genes = merged_df.columns.drop("Cluster")
        unique_clusters = sorted(merged_df["Cluster"].unique())
        volcano_frames: list[pd.DataFrame] = []
        top_genes: list[str] = []

        for target_cluster in unique_clusters:
            group_a = merged_df[merged_df["Cluster"] == target_cluster][genes]
            group_b = merged_df[merged_df["Cluster"] != target_cluster][genes]

            if len(group_a) < 2 or len(group_b) < 2:
                cluster_res_df = pd.DataFrame(
                    {
                        "cluster": target_cluster,
                        "gene": genes.astype(str),
                        "logFC": 0.0,
                        "t_pvalue": 1.0,
                        "negLog10P": 0.0,
                    }
                )
                volcano_frames.append(cluster_res_df)
                continue

            mean_a = group_a.mean(axis=0)
            mean_b = group_b.mean(axis=0)
            log_fc = mean_a - mean_b
            _, p_values = stats.ttest_ind(group_a, group_b, axis=0, equal_var=False, nan_policy="omit")

            cluster_res_df = pd.DataFrame(
                {
                    "cluster": target_cluster,
                    "gene": genes.astype(str),
                    "logFC": log_fc.to_numpy(dtype=float),
                    "t_pvalue": p_values,
                }
            )
            cluster_res_df["t_pvalue"] = cluster_res_df["t_pvalue"].fillna(1.0).clip(lower=0)
            cluster_res_df["negLog10P"] = -np.log10(cluster_res_df["t_pvalue"] + 1e-300)
            volcano_frames.append(cluster_res_df)

            significant = cluster_res_df[(cluster_res_df["t_pvalue"] < 0.05) & (cluster_res_df["logFC"] > 0.5)]
            for gene in significant.sort_values(["logFC", "t_pvalue"], ascending=[False, True]).head(10)["gene"]:
                if gene not in top_genes:
                    top_genes.append(str(gene))

        volcano_df = pd.concat(volcano_frames, ignore_index=True) if volcano_frames else pd.DataFrame()
        volcano_path = plot_path(request.session_id, DIFFERENTIAL_VOLCANO_FILE)
        volcano_df.to_parquet(volcano_path, index=False)

        heatmap_path = plot_path(request.session_id, DIFFERENTIAL_HEATMAP_FILE)
        if top_genes:
            heatmap_df = merged_df[top_genes + ["Cluster"]].copy()
            feature_values = heatmap_df[top_genes]
            std = feature_values.std(axis=0).replace(0, np.nan)
            heatmap_df[top_genes] = ((feature_values - feature_values.mean(axis=0)) / std).replace([np.inf, -np.inf], np.nan).fillna(0)
            heatmap_df = heatmap_df.sort_values("Cluster")
            heatmap_df.insert(0, "sample_name", heatmap_df.index.astype(str))
            heatmap_df.to_parquet(heatmap_path, index=False)
        else:
            pd.DataFrame(columns=["sample_name", "Cluster"]).to_parquet(heatmap_path, index=False)

        clusters = [int(c) for c in unique_clusters]
        selected_cluster = clusters[0] if clusters else 0
        write_json(
            plot_path(request.session_id, DIFFERENTIAL_META_FILE),
            {"omics_type": request.omics_type, "clusters": clusters, "top_genes": top_genes},
        )

        try:
            volcano_svg = render_volcano_svg(str(volcano_path), selected_cluster)
        except Exception as exc:
            volcano_svg = empty_svg(f"Volcano plot failed: {exc}", "Differential Volcano")

        try:
            heatmap_svg = run_r_svg("differential_heatmap.R", [heatmap_path])
        except Exception as exc:
            heatmap_svg = empty_svg(f"Heatmap failed: {exc}", "Differential Heatmap")

        return {
            "status": "success",
            "omics_type": request.omics_type,
            "clusters": clusters,
            "selected_cluster": selected_cluster,
            "volcano_svg": volcano_svg,
            "heatmap_svg": heatmap_svg,
            "n_features": int(len(genes)),
            "n_top_genes": int(len(top_genes)),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
