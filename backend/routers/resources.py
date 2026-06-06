"""资源页面箱线图接口（无状态）。

与 analysis 系列路由不同，本路由不依赖 session_id / upload 机制：用户在前端粘贴
「名称,数值,数值,...」格式文本并选择变体，直接渲染并下载箱线图。
"""

import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from plots.base import media_type_for_format, normalize_plot_format
from plots.resource_boxplot import render_bytes, render_svg
from plots.resource_heatmap import render_bytes as render_heatmap_bytes, render_svg as render_heatmap_svg


router = APIRouter()


class BoxplotRequest(BaseModel):
    data: str
    variant: str = "pvalues"


class BoxplotDownloadRequest(BoxplotRequest):
    format: str = "png"


@router.post("/api/resources/boxplot")
async def resource_boxplot(request: BoxplotRequest):
    try:
        svg = render_svg(request.data, request.variant)
        return {"status": "success", "svg": svg, "variant": request.variant}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/resources/boxplot/download")
async def resource_boxplot_download(request: BoxplotDownloadRequest):
    try:
        fmt = normalize_plot_format(request.format)
        payload = render_bytes(request.data, request.variant, fmt)
        headers = {
            "Content-Disposition": f'attachment; filename="boxplot_{request.variant}.{fmt}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(
            io.BytesIO(payload),
            media_type=media_type_for_format(fmt),
            headers=headers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class HeatmapRequest(BaseModel):
    data: str


class HeatmapDownloadRequest(HeatmapRequest):
    format: str = "png"


@router.post("/api/resources/heatmap")
async def resource_heatmap(request: HeatmapRequest):
    try:
        svg = render_heatmap_svg(request.data)
        return {"status": "success", "svg": svg}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/resources/heatmap/download")
async def resource_heatmap_download(request: HeatmapDownloadRequest):
    try:
        fmt = normalize_plot_format(request.format)
        payload = render_heatmap_bytes(request.data, fmt)
        headers = {
            "Content-Disposition": f'attachment; filename="heatmap.{fmt}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(
            io.BytesIO(payload),
            media_type=media_type_for_format(fmt),
            headers=headers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
