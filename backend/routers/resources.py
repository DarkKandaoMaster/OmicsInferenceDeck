"""资源页面箱线图接口（无状态）。

与 analysis 系列路由不同，本路由不依赖 session_id / upload 机制：用户在前端粘贴
「名称,数值,数值,...」格式文本并选择变体，直接渲染并下载箱线图。
"""

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from plots.base import media_type_for_format, normalize_plot_format
from plots.resource_boxplot import render_bytes, render_svg
from plots.resource_heatmap import render_bytes as render_heatmap_bytes, render_svg as render_heatmap_svg
from plots.resource_stitch import make_preview as stitch_make_preview, stitch as stitch_bytes


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


# ---------------------------------------------------------------------------
# 图表拼接（multipart 上传多个同格式图表，拼成最多 3 行网格）
# ---------------------------------------------------------------------------

async def _collect_stitch_files(
    files: list[UploadFile], fmt: str
) -> tuple[str, list[tuple[str, bytes]]]:
    normalized = normalize_plot_format(fmt)
    if not files:
        raise ValueError("没有可拼接的图表")
    collected: list[tuple[str, bytes]] = []
    for upload in files:
        name = upload.filename or ""
        suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if suffix != normalized:
            raise ValueError("不能上传不同格式的图表")
        collected.append((name, await upload.read()))
    return normalized, collected


@router.post("/api/resources/stitch")
async def resource_stitch(
    files: list[UploadFile] = File(...),
    row1: int = Form(...),
    row2: int = Form(...),
    row3: int = Form(...),
    format: str = Form("png"),
):
    try:
        normalized, collected = await _collect_stitch_files(files, format)
        preview_format, preview = stitch_make_preview(
            collected, [row1, row2, row3], normalized
        )
        return {
            "status": "success",
            "preview_format": preview_format,
            "preview": preview,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/resources/stitch/download")
async def resource_stitch_download(
    files: list[UploadFile] = File(...),
    row1: int = Form(...),
    row2: int = Form(...),
    row3: int = Form(...),
    format: str = Form("png"),
):
    try:
        normalized, collected = await _collect_stitch_files(files, format)
        payload = stitch_bytes(collected, [row1, row2, row3], normalized)
        headers = {
            "Content-Disposition": f'attachment; filename="stitched.{normalized}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(
            io.BytesIO(payload),
            media_type=media_type_for_format(normalized),
            headers=headers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
