"""比较不同聚类之间的组学特征差异。

本文件读取 upload.py 保存的组学数据和 run.py 生成的聚类结果，
对每个聚类做“该聚类 vs 其他聚类”的差异分析。它会保存火山图和热图所需的数据，
供 enrichment.py 继续做富集分析，也供 plots.py 重新绘图或下载。
"""

import json
import subprocess
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from routers.upload import OMICS_DATA_FILE, load_frame_dict

from plots.base import (
    CLUSTER_RESULT_FILE,
    DIFFERENTIAL_HEATMAP_FILE,
    DIFFERENTIAL_META_FILE,
    DIFFERENTIAL_VOLCANO_FILE,
    empty_svg,
    plot_path,
    run_r_svg,
)
from plots.differential_volcano import render_svg as render_volcano_svg


router = APIRouter()
DIFFERENTIAL_SCRIPT = Path(__file__).with_name("differential.R")
DIFFERENTIAL_INPUT_FILE = "differential_input.parquet"


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


def _parse_r_payload(result: subprocess.CompletedProcess[str], fallback_message: str) -> dict:
    stdout = result.stdout.strip()
    if result.returncode != 0:
        message = stdout or result.stderr.strip() or fallback_message
        try:
            message = json.loads(stdout).get("error", message)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(message)

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid R differential output: {stdout[:500]}") from exc

    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload


def _run_differential_r(input_path: Path, volcano_path: Path, heatmap_path: Path) -> dict:
    if not DIFFERENTIAL_SCRIPT.exists():
        raise FileNotFoundError(f"R differential script not found: {DIFFERENTIAL_SCRIPT}")

    result = subprocess.run(
        ["Rscript", str(DIFFERENTIAL_SCRIPT), str(input_path), str(volcano_path), str(heatmap_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
    )
    return _parse_r_payload(result, "R differential script failed")


@router.post("/api/differential_analysis")
async def run_differential_analysis(request: DifferentialAnalysisRequest):
    try:
        df = _load_omics_frame(request.session_id, request.omics_type)
        df.index = df.index.astype(str)
        cluster_info = _load_cluster_info(request.session_id)

        merged_df = df.join(cluster_info, how="inner")
        if merged_df.empty:
            raise ValueError("No matching samples between omics data and clustering result.")

        volcano_path = plot_path(request.session_id, DIFFERENTIAL_VOLCANO_FILE)
        heatmap_path = plot_path(request.session_id, DIFFERENTIAL_HEATMAP_FILE)
        input_path = plot_path(request.session_id, DIFFERENTIAL_INPUT_FILE)
        genes = merged_df.columns.drop("Cluster")
        r_input_df = merged_df.copy()
        r_input_df.insert(0, "sample_name", r_input_df.index.astype(str))
        r_input_df.to_parquet(input_path, index=False)

        payload = _run_differential_r(input_path, volcano_path, heatmap_path)

        clusters = [int(c) for c in payload.get("clusters", [])]
        selected_cluster = int(payload.get("selected_cluster", clusters[0] if clusters else 0))
        top_genes = [str(gene) for gene in payload.get("top_genes", [])]
        plot_path(request.session_id, DIFFERENTIAL_META_FILE).write_text(
            json.dumps({"omics_type": request.omics_type, "clusters": clusters, "top_genes": top_genes}, ensure_ascii=False, indent=2),
            encoding="utf-8",
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
            "n_features": int(payload.get("n_features", len(genes))),
            "n_top_genes": int(payload.get("n_top_genes", len(top_genes))),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
