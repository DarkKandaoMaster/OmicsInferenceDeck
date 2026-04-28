import datetime
import json
import os
import subprocess

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

from plots.base import CLUSTER_RESULT_FILE, plot_path


router = APIRouter()


class MetricsRequest(BaseModel):
    session_id: str


def _fallback_metrics() -> dict:
    return {"silhouette": -1, "calinski": -1, "davies": -1, "dunn": -1, "xb": -1, "s_dbw": -1}


def compute_r_metrics(parquet_path: str) -> dict:
    r_script = os.path.join(os.path.dirname(__file__), "analysis.R")
    r_script = os.path.abspath(r_script)
    if not os.path.exists(r_script):
        return {"dunn": -1, "xb": -1, "s_dbw": -1}

    try:
        result = subprocess.run(
            ["Rscript", r_script, parquet_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3600,
        )
        if result.returncode != 0:
            return {"dunn": -1, "xb": -1, "s_dbw": -1}
        r_output = json.loads(result.stdout.strip())
        if "error" in r_output:
            return {"dunn": -1, "xb": -1, "s_dbw": -1}
        return {
            "dunn": r_output.get("dunn", -1),
            "xb": r_output.get("xb", -1),
            "s_dbw": r_output.get("s_dbw", -1),
        }
    except Exception:
        return {"dunn": -1, "xb": -1, "s_dbw": -1}


def compute_cluster_metrics(result_path: str) -> tuple[dict, int, int]:
    df_result = pd.read_parquet(result_path)
    labels = df_result["label"].to_numpy()
    emb_cols = [c for c in df_result.columns if c.startswith("emb_")]
    embeddings = df_result[emb_cols].to_numpy(dtype=float)

    n_unique = len(np.unique(labels))
    if n_unique < 2 or len(labels) <= n_unique:
        return _fallback_metrics(), int(len(df_result)), int(len(emb_cols))

    metrics_scores = {
        "silhouette": round(float(silhouette_score(embeddings, labels)), 4),
        "calinski": round(float(calinski_harabasz_score(embeddings, labels)), 4),
        "davies": round(float(davies_bouldin_score(embeddings, labels)), 4),
    }
    r_metrics = compute_r_metrics(result_path)
    for key in ("dunn", "xb", "s_dbw"):
        val = r_metrics[key]
        metrics_scores[key] = None if isinstance(val, float) and np.isnan(val) else val

    return metrics_scores, int(len(df_result)), int(len(emb_cols))


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
