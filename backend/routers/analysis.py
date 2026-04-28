import datetime
import json
import os
import subprocess

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

from plots.base import CLUSTER_RESULT_FILE, empty_svg, plot_path
from plots.cluster_scatter import render_svg as render_cluster_scatter_svg


router = APIRouter()


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


class AnalysisRequest(BaseModel):
    session_id: str
    reduction: str = "PCA"
    random_state: int = 42


@router.post("/api/analysis")
async def analysis(request: AnalysisRequest):
    seed = request.random_state if request.random_state != -1 else None

    try:
        result_path = plot_path(request.session_id, CLUSTER_RESULT_FILE)
        if not result_path.exists():
            raise FileNotFoundError("cluster_result.parquet not found. Please run clustering first.")

        df_result = pd.read_parquet(result_path)
        labels = df_result["label"].to_numpy()
        emb_cols = [c for c in df_result.columns if c.startswith("emb_")]
        embeddings = df_result[emb_cols].to_numpy(dtype=float)

        n_unique = len(np.unique(labels))
        if n_unique >= 2 and len(labels) > n_unique:
            metrics_scores = {
                "silhouette": round(float(silhouette_score(embeddings, labels)), 4),
                "calinski": round(float(calinski_harabasz_score(embeddings, labels)), 4),
                "davies": round(float(davies_bouldin_score(embeddings, labels)), 4),
            }
            r_metrics = compute_r_metrics(str(result_path))
            for key in ("dunn", "xb", "s_dbw"):
                val = r_metrics[key]
                metrics_scores[key] = None if isinstance(val, float) and np.isnan(val) else val
        else:
            metrics_scores = {"silhouette": -1, "calinski": -1, "davies": -1, "dunn": -1, "xb": -1, "s_dbw": -1}

        try:
            cluster_svg = render_cluster_scatter_svg(str(result_path), request.reduction, seed)
        except Exception as exc:
            cluster_svg = empty_svg(f"Cluster plot failed: {exc}", "Cluster Scatter")

        return {
            "status": "success",
            "message": f"Analysis completed. Reduction: {request.reduction}.",
            "server_time": datetime.datetime.now().isoformat(),
            "data": {
                "method": "Clustering",
                "metrics": metrics_scores,
                "n_samples": int(len(df_result)),
                "n_features": int(len(emb_cols)),
                "reduction": request.reduction,
                "plots": {
                    "cluster_scatter": cluster_svg,
                },
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Evaluation/plotting failed: {str(e)}")
