import io
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from plots.base import (
    CLUSTER_RESULT_FILE,
    DIFFERENTIAL_HEATMAP_FILE,
    DIFFERENTIAL_VOLCANO_FILE,
    PARAMETER_SEARCH_FILE,
    SURVIVAL_DATA_FILE,
    empty_svg,
    enrichment_file,
    figure_to_bytes,
    media_type_for_format,
    plot_path,
    read_json,
    run_r_plot_bytes,
    run_r_svg,
    session_dir,
)
from plots.cluster_scatter import build_figure as build_cluster_scatter_figure
from plots.cluster_scatter import render_svg as render_cluster_scatter_svg
from plots.differential_volcano import build_figure as build_volcano_figure
from plots.differential_volcano import render_svg as render_volcano_svg
from plots.parameter_surface import build_figure as build_parameter_figure
from plots.parameter_surface import render_svg as render_parameter_svg
from plots.survival_curve import build_figure as build_survival_figure
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


class PlotDownloadRequest(BaseModel):
    session_id: str
    plot_type: str
    format: str
    reduction: str = "PCA"
    random_state: int = 42
    cluster_id: int | None = None
    database: str | None = None
    mode: str = "combined"
    x_param: str | None = None
    y_param: str | None = None


def _seed_or_none(random_state: int) -> int | None:
    return None if random_state == -1 else random_state


def _require_cluster_id(request: PlotDownloadRequest) -> int:
    if request.cluster_id is None:
        raise ValueError("cluster_id is required for this plot")
    return int(request.cluster_id)


def _require_database(request: PlotDownloadRequest) -> str:
    if not request.database:
        raise ValueError("database is required for this plot")
    return request.database


def _require_x_param(request: PlotDownloadRequest) -> str:
    if not request.x_param:
        raise ValueError("x_param is required for parameter_surface")
    return request.x_param


def _download_filename(stem: str, file_format: str) -> str:
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "plot"
    return f"{safe_stem}.{file_format.lower()}"


def _render_download_payload(request: PlotDownloadRequest) -> tuple[bytes, str]:
    plot_type = request.plot_type.strip().lower()
    file_format = request.format.strip().lower()

    if plot_type == "cluster_scatter":
        path = plot_path(request.session_id, CLUSTER_RESULT_FILE)
        fig = build_cluster_scatter_figure(str(path), request.reduction, _seed_or_none(request.random_state))
        return figure_to_bytes(fig, file_format), f"cluster_scatter_{request.reduction}"

    if plot_type == "differential_volcano":
        cluster_id = _require_cluster_id(request)
        path = plot_path(request.session_id, DIFFERENTIAL_VOLCANO_FILE)
        fig = build_volcano_figure(str(path), cluster_id)
        return figure_to_bytes(fig, file_format), f"differential_volcano_cluster_{cluster_id}"

    if plot_type == "survival_curve":
        path = plot_path(request.session_id, SURVIVAL_DATA_FILE)
        meta_path = plot_path(request.session_id, "survival_meta.json")
        p_value = read_json(meta_path).get("p_value") if meta_path.exists() else None
        fig = build_survival_figure(str(path), p_value)
        return figure_to_bytes(fig, file_format), "survival_curve"

    if plot_type == "parameter_surface":
        x_param = _require_x_param(request)
        path = plot_path(request.session_id, PARAMETER_SEARCH_FILE)
        fig = build_parameter_figure(str(path), x_param, request.y_param)
        y_suffix = f"_{request.y_param}" if request.y_param else ""
        return figure_to_bytes(fig, file_format), f"parameter_surface_{x_param}{y_suffix}"

    if plot_type == "differential_heatmap":
        path = plot_path(request.session_id, DIFFERENTIAL_HEATMAP_FILE)
        payload = run_r_plot_bytes("differential_heatmap.R", [path], file_format, session_dir(request.session_id))
        return payload, "differential_heatmap"

    if plot_type == "enrichment_bar":
        database = _require_database(request)
        cluster_id = _require_cluster_id(request)
        path = plot_path(request.session_id, enrichment_file(database))
        payload = run_r_plot_bytes("enrichment_bar.R", [path, cluster_id], file_format, session_dir(request.session_id))
        return payload, f"enrichment_{database.upper()}_bar_cluster_{cluster_id}"

    if plot_type == "enrichment_bubble":
        database = _require_database(request)
        mode = request.mode if request.mode in {"combined", "by_gene"} else "combined"
        path = plot_path(request.session_id, enrichment_file(database))
        payload = run_r_plot_bytes("enrichment_bubble.R", [path, mode], file_format, session_dir(request.session_id))
        return payload, f"enrichment_{database.upper()}_bubble_{mode}"

    raise ValueError(f"Unsupported plot_type: {request.plot_type}")


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


@router.post("/api/plots/download")
async def download_plot(request: PlotDownloadRequest):
    try:
        file_format = request.format.strip().lower()
        payload, filename_stem = _render_download_payload(request)
        filename = _download_filename(filename_stem, file_format)
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(
            io.BytesIO(payload),
            media_type=media_type_for_format(file_format),
            headers=headers,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
