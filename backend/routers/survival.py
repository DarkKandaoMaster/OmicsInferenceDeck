"""根据聚类结果和临床数据准备生存分析结果。

本文件读取 upload.py 保存的临床数据，以及 run.py 或 evaluate_run.py 生成的
cluster_result.parquet，把样本的生存时间、结局和聚类标签合并起来。合并后的
数据会保存为 survival 数据文件，并返回可在前端显示的生存曲线 SVG。
"""

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from routers.upload import CLINICAL_DATA_FILE, load_frame_dict

from plots.base import CLUSTER_RESULT_FILE, SURVIVAL_DATA_FILE, empty_svg, plot_path, read_json
from plots.survival_curve import render_svg as render_survival_svg


router = APIRouter()


class SurvivalRequest(BaseModel):
    session_id: str
    sample: list[str] | None = None
    labels: list[int] | None = None


@router.post("/api/survival_analysis")
async def run_survival_analysis(request: SurvivalRequest):
    try:
        clinical_path = plot_path(request.session_id, CLINICAL_DATA_FILE)
        if not clinical_path.exists():
            raise FileNotFoundError("clinical_data.parquet not found. Please upload clinical data first.")

        cluster_path = plot_path(request.session_id, CLUSTER_RESULT_FILE)
        if not cluster_path.exists():
            raise FileNotFoundError("cluster_result.parquet not found. Please run clustering first.")

        clinical_dict = load_frame_dict(clinical_path)
        clinical_df = list(clinical_dict.values())[0].copy()
        clinical_df.index = clinical_df.index.astype(str)

        cluster_df = pd.read_parquet(cluster_path)[["sample_name", "label"]].copy()
        cluster_df["sample_name"] = cluster_df["sample_name"].astype(str)
        cluster_df = cluster_df.rename(columns={"label": "Cluster"}).set_index("sample_name")

        merged_df = clinical_df.join(cluster_df, how="inner")
        if merged_df.empty:
            raise ValueError("No matching samples between clinical data and clustering result.")

        merged_df = merged_df[["OS.time", "OS", "Cluster"]].copy()
        merged_df["OS.time"] = pd.to_numeric(merged_df["OS.time"], errors="coerce")
        merged_df["OS"] = pd.to_numeric(merged_df["OS"], errors="coerce")
        merged_df = merged_df.dropna(subset=["OS.time", "OS", "Cluster"])
        if merged_df.empty:
            raise ValueError("Matched clinical data contains no valid OS/OS.time rows.")

        survival_data = merged_df.reset_index().rename(columns={"index": "sample_name"})
        survival_path = plot_path(request.session_id, SURVIVAL_DATA_FILE)
        survival_data.to_parquet(survival_path, index=False)

        meta_path = plot_path(request.session_id, "survival_meta.json")
        p_value = read_json(meta_path).get("p_value") if meta_path.exists() else None

        lost_samples = int(len(cluster_df) - len(merged_df))
        try:
            survival_svg = render_survival_svg(str(survival_path), p_value)
        except Exception as exc:
            survival_svg = empty_svg(f"Survival plot failed: {exc}", "Survival Curve")

        return {
            "status": "success",
            "p_value": p_value,
            "survival_svg": survival_svg,
            "n_samples": int(len(merged_df)),
            "lost_samples": lost_samples,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
