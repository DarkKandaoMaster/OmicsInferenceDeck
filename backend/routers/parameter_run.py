import itertools
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from lifelines.statistics import multivariate_logrank_test
from pydantic import BaseModel

from algorithms import load_algorithm
from routers.upload import CLINICAL_DATA_FILE, OMICS_DATA_FILE, load_frame_dict
from plots.base import PARAMETER_SEARCH_FILE, PARAMETER_SEARCH_META_FILE, empty_svg, plot_path, write_json
from plots.parameter_surface import render_svg as render_parameter_svg


router = APIRouter()


class ParameterSearchRequest(BaseModel):
    session_id: str
    algorithm: str
    param_grid: dict[str, list]
    random_state: int = 42


@router.post("/api/parameter_search")
async def run_parameter_search(request: ParameterSearchRequest):
    try:
        omics_path = plot_path(request.session_id, OMICS_DATA_FILE)
        clinical_path = plot_path(request.session_id, CLINICAL_DATA_FILE)
        if not omics_path.exists():
            raise FileNotFoundError("omics_data.parquet not found.")
        if not clinical_path.exists():
            raise FileNotFoundError("clinical_data.parquet not found.")

        omics_dict = load_frame_dict(omics_path)
        clinical_dict = load_frame_dict(clinical_path)
        clinical_df = list(clinical_dict.values())[0].copy()
        clinical_df.index = clinical_df.index.astype(str)

        algo_class = load_algorithm(request.algorithm)
        param_names = list(request.param_grid.keys())
        param_values = list(request.param_grid.values())
        combinations = list(itertools.product(*param_values))

        records: list[dict] = []
        best_score = -1.0
        best_params: dict | None = None

        for combo in combinations:
            params = dict(zip(param_names, combo))
            params_with_seed = {**params, "random_state": request.random_state}
            try:
                algo_instance = algo_class(**params_with_seed)
                labels, _, sample_names = algo_instance.fit_predict(omics_dict)
                cluster_df = pd.DataFrame({"Cluster": labels}, index=[str(s) for s in sample_names])
                merged = clinical_df.join(cluster_df, how="inner")
                if merged.empty or merged["Cluster"].nunique() < 2:
                    score = 0.0
                else:
                    lr_results = multivariate_logrank_test(merged["OS.time"], merged["Cluster"], merged["OS"])
                    p_val = float(lr_results.p_value) if np.isfinite(lr_results.p_value) else 1.0
                    score = float(-np.log10(p_val + 1e-300))
            except Exception:
                score = 0.0

            record = {k: v for k, v in params.items()}
            record["score"] = score
            records.append(record)

            if score > best_score:
                best_score = score
                best_params = {k: v for k, v in params.items()}

        result_df = pd.DataFrame(records)
        result_path = plot_path(request.session_id, PARAMETER_SEARCH_FILE)
        result_df.to_parquet(result_path, index=False)

        meta = {"best_params": best_params or {}, "best_score": best_score, "param_names": param_names}
        write_json(plot_path(request.session_id, PARAMETER_SEARCH_META_FILE), meta)

        x_param = param_names[0] if param_names else ""
        y_param = param_names[1] if len(param_names) > 1 else None
        try:
            plot_svg = render_parameter_svg(str(result_path), x_param, y_param)
        except Exception as exc:
            plot_svg = empty_svg(f"Parameter plot failed: {exc}", "Parameter Sensitivity")

        return {
            "status": "success",
            "best_params": best_params or {},
            "best_score": best_score,
            "param_names": param_names,
            "x_param": x_param,
            "y_param": y_param or "",
            "plot_svg": plot_svg,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
