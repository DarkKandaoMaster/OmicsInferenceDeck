from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plots.base import (
    CLUSTER_RESULT_FILE,
    DIFFERENTIAL_HEATMAP_FILE,
    DIFFERENTIAL_VOLCANO_FILE,
    PARAMETER_SEARCH_FILE,
    SURVIVAL_DATA_FILE,
    empty_svg,
    enrichment_file,
    plot_path,
    read_json,
    run_r_svg,
)
from plots.cluster_scatter import render_svg as render_cluster_scatter_svg
from plots.differential_volcano import render_svg as render_volcano_svg
from plots.parameter_surface import render_svg as render_parameter_svg
from plots.survival_curve import render_svg as render_survival_svg


router = APIRouter()


class ClusterPlotRequest(BaseModel):
    session_id: str
    reduction: str = "PCA"
    random_state: int = 42


class ClusterSpecificPlotRequest(BaseModel):
    session_id: str
    cluster_id: int


class SessionPlotRequest(BaseModel):
    session_id: str


class EnrichmentBarRequest(BaseModel):
    session_id: str
    database: str
    cluster_id: int


class EnrichmentBubbleRequest(BaseModel):
    session_id: str
    database: str
    mode: str = "combined"


class ParameterPlotRequest(BaseModel):
    session_id: str
    x_param: str
    y_param: str | None = None


@router.post("/api/plots/cluster_scatter")
async def cluster_scatter(request: ClusterPlotRequest):
    try:
        path = plot_path(request.session_id, CLUSTER_RESULT_FILE)
        return {"status": "success", "svg": render_cluster_scatter_svg(str(path), request.reduction, request.random_state)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/plots/differential_volcano")
async def differential_volcano(request: ClusterSpecificPlotRequest):
    try:
        path = plot_path(request.session_id, DIFFERENTIAL_VOLCANO_FILE)
        return {"status": "success", "svg": render_volcano_svg(str(path), request.cluster_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/plots/differential_heatmap")
async def differential_heatmap(request: SessionPlotRequest):
    try:
        path = plot_path(request.session_id, DIFFERENTIAL_HEATMAP_FILE)
        return {"status": "success", "svg": run_r_svg("differential_heatmap.R", [path])}
    except Exception as e:
        return {"status": "success", "svg": empty_svg(f"Heatmap failed: {e}", "Differential Heatmap")}


@router.post("/api/plots/enrichment_bar")
async def enrichment_bar(request: EnrichmentBarRequest):
    try:
        path = plot_path(request.session_id, enrichment_file(request.database))
        return {"status": "success", "svg": run_r_svg("enrichment_bar.R", [path, request.cluster_id])}
    except Exception as e:
        return {"status": "success", "svg": empty_svg(f"Enrichment bar plot failed: {e}", "Enrichment Bar")}


@router.post("/api/plots/enrichment_bubble")
async def enrichment_bubble(request: EnrichmentBubbleRequest):
    try:
        mode = request.mode if request.mode in {"combined", "by_gene"} else "combined"
        path = plot_path(request.session_id, enrichment_file(request.database))
        return {"status": "success", "svg": run_r_svg("enrichment_bubble.R", [path, mode])}
    except Exception as e:
        return {"status": "success", "svg": empty_svg(f"Enrichment bubble plot failed: {e}", "Enrichment Bubble")}


@router.post("/api/plots/survival_curve")
async def survival_curve(request: SessionPlotRequest):
    try:
        path = plot_path(request.session_id, SURVIVAL_DATA_FILE)
        meta_path = plot_path(request.session_id, "survival_meta.json")
        p_value = read_json(meta_path).get("p_value") if meta_path.exists() else None
        return {"status": "success", "svg": render_survival_svg(str(path), p_value)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/plots/parameter_surface")
async def parameter_surface(request: ParameterPlotRequest):
    try:
        path = plot_path(request.session_id, PARAMETER_SEARCH_FILE)
        return {"status": "success", "svg": render_parameter_svg(str(path), request.x_param, request.y_param)}
    except Exception as e:
        return {"status": "success", "svg": empty_svg(f"Parameter plot failed: {e}", "Parameter Sensitivity")}
