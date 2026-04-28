import datetime
import json
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plots.base import CLUSTER_RESULT_FILE, plot_path


router = APIRouter()
METRICS_SCRIPT = Path(__file__).resolve().parents[1] / "metrics" / "cluster_metrics.R"
METRIC_KEYS = ("silhouette", "calinski", "davies", "dunn", "xb", "s_dbw")


class MetricsRequest(BaseModel):
    session_id: str


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

    stdout = result.stdout.strip()
    if result.returncode != 0:
        message = stdout or result.stderr.strip() or "R metrics script failed"
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

    metrics = payload.get("metrics", {})
    metrics_scores = {key: metrics.get(key, -1) for key in METRIC_KEYS}

    return metrics_scores, int(payload.get("n_samples", 0)), int(payload.get("n_features", 0))


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
