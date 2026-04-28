import datetime
import json
import subprocess
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plots.base import CLUSTER_RESULT_FILE, plot_path, write_json
from routers.upload import CLINICAL_DATA_FILE, load_frame_dict


router = APIRouter()
METRICS_SCRIPT = Path(__file__).resolve().parents[1] / "metrics" / "cluster_metrics.R"
CLINICAL_METRICS_SCRIPT = Path(__file__).resolve().parents[1] / "metrics" / "clinical_metrics.R"
METRIC_KEYS = ("silhouette", "silhouette_cluster", "calinski", "davies", "dunn", "xb", "s_dbw")
CLINICAL_METRICS_INPUT_FILE = "clinical_metrics_input.parquet"


class MetricsRequest(BaseModel):
    session_id: str


def parse_r_payload(result: subprocess.CompletedProcess[str], fallback_message: str) -> dict:
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
        raise RuntimeError(f"Invalid R metrics output: {stdout[:500]}") from exc

    if "error" in payload:
        raise RuntimeError(str(payload["error"]))

    return payload


def compute_cluster_metrics(result_path: str) -> tuple[dict, int, int]:
    if not METRICS_SCRIPT.exists():
        raise FileNotFoundError(f"R metrics script not found: {METRICS_SCRIPT}")

    result = subprocess.run(
        ["Rscript", str(METRICS_SCRIPT), result_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
    )

    payload = parse_r_payload(result, "R metrics script failed")

    metrics = payload.get("metrics", {})
    metrics_scores = {key: metrics.get(key, -1) for key in METRIC_KEYS}

    return metrics_scores, int(payload.get("n_samples", 0)), int(payload.get("n_features", 0))


def build_clinical_metrics_input(session_id: str) -> tuple[Path, int, int]:
    clinical_path = plot_path(session_id, CLINICAL_DATA_FILE)
    if not clinical_path.exists():
        raise FileNotFoundError("clinical_data.parquet not found. Please upload clinical data first.")

    cluster_path = plot_path(session_id, CLUSTER_RESULT_FILE)
    if not cluster_path.exists():
        raise FileNotFoundError("cluster_result.parquet not found. Please run clustering first.")

    clinical_dict = load_frame_dict(clinical_path)
    clinical_df = list(clinical_dict.values())[0].copy()
    clinical_df.index = clinical_df.index.astype(str)

    reserved_columns = {"sample_name", "Cluster"}
    rename_map = {column: f"clinical_{column}" for column in clinical_df.columns if column in reserved_columns}
    if rename_map:
        clinical_df = clinical_df.rename(columns=rename_map)

    cluster_df = pd.read_parquet(cluster_path)[["sample_name", "label"]].copy()
    cluster_df["sample_name"] = cluster_df["sample_name"].astype(str)
    cluster_df = cluster_df.rename(columns={"label": "Cluster"}).set_index("sample_name")

    merged_df = clinical_df.join(cluster_df, how="inner")
    if merged_df.empty:
        raise ValueError("No matching samples between clinical data and clustering result.")
    if "OS" not in merged_df.columns or "OS.time" not in merged_df.columns:
        raise ValueError("clinical data must contain 'OS' and 'OS.time' columns.")

    matched_samples = int(len(merged_df))
    lost_samples = int(len(cluster_df) - matched_samples)
    merged_df.index.name = "sample_name"
    merged_df = merged_df.reset_index()

    front_columns = [column for column in ("sample_name", "Cluster", "OS", "OS.time") if column in merged_df.columns]
    merged_df = merged_df[front_columns + [column for column in merged_df.columns if column not in front_columns]]

    for column in merged_df.columns:
        if column == "sample_name" or not pd.api.types.is_numeric_dtype(merged_df[column]):
            merged_df[column] = merged_df[column].astype("string")

    input_path = plot_path(session_id, CLINICAL_METRICS_INPUT_FILE)
    merged_df.to_parquet(input_path, index=False)
    return input_path, matched_samples, lost_samples


def compute_clinical_metrics(input_path: str) -> dict:
    if not CLINICAL_METRICS_SCRIPT.exists():
        raise FileNotFoundError(f"R clinical metrics script not found: {CLINICAL_METRICS_SCRIPT}")

    result = subprocess.run(
        ["Rscript", str(CLINICAL_METRICS_SCRIPT), input_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
    )

    return parse_r_payload(result, "R clinical metrics script failed")


@router.post("/api/metrics")
async def cluster_metrics(request: MetricsRequest):
    try:
        result_path = plot_path(request.session_id, CLUSTER_RESULT_FILE)
        if not result_path.exists():
            raise FileNotFoundError("cluster_result.parquet not found. Please run clustering first.")

        metrics_scores, n_samples, n_features = compute_cluster_metrics(str(result_path))
        return {
            "status": "success",
            "message": "Cluster metrics calculated.",
            "server_time": datetime.datetime.now().isoformat(),
            "data": {
                "method": "Clustering",
                "metrics": metrics_scores,
                "n_samples": n_samples,
                "n_features": n_features,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Metrics calculation failed: {str(e)}")


@router.post("/api/metrics/clinical")
async def clinical_metrics(request: MetricsRequest):
    try:
        input_path, matched_samples, lost_samples = build_clinical_metrics_input(request.session_id)
        clinical_metrics_scores = compute_clinical_metrics(str(input_path))
        clinical_metrics_scores["matched_samples"] = matched_samples
        clinical_metrics_scores["lost_samples"] = lost_samples

        lrt = clinical_metrics_scores.get("lrt") or {}
        write_json(plot_path(request.session_id, "survival_meta.json"), {"p_value": lrt.get("p_value")}) #方便后续绘制生存曲线时能显示这里计算出的p值

        return {
            "status": "success",
            "message": "Clinical metrics calculated.",
            "server_time": datetime.datetime.now().isoformat(),
            "data": {
                "method": "Clinical",
                "clinical_metrics": clinical_metrics_scores,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Clinical metrics calculation failed: {str(e)}")
