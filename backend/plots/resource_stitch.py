"""资源页面「图表拼接」逻辑（无状态）。

把多个同一格式（png / svg / pdf）的图表，按上传顺序从左到右、从上到下
填入最多 3 行的网格，再拼接成一张大图。

- PNG：Pillow
- PDF：PyMuPDF(fitz)
- SVG：svgutils

三种格式统一的摆放规则：严格按 `files` 的上传顺序，第 1 行放前 r1 个、
第 2 行放接下来 r2 个、第 3 行放剩下 r3 个；行与行自上而下排列；不做任何重排序。
同一行内的图先缩放到统一高度（取该行最大高度）再水平拼接；各行再按最大行宽
居中、垂直堆叠。
"""

import base64
import io
import re

import fitz  # PyMuPDF
from PIL import Image
from svgutils.transform import SVGFigure, fromstring

from plots.base import normalize_plot_format


# ---------------------------------------------------------------------------
# 通用校验
# ---------------------------------------------------------------------------

def _validate(files: list[tuple[str, bytes]], rows: list[int]) -> tuple[int, int, int]:
    if not files:
        raise ValueError("没有可拼接的图表")
    if len(rows) != 3:
        raise ValueError("rows 必须是三个整数 [r1, r2, r3]")
    if any(r < 0 for r in rows):
        raise ValueError("行数不能为负数")
    r1, r2, r3 = rows
    if r1 + r2 + r3 != len(files):
        raise ValueError(f"三行之和（{r1 + r2 + r3}）必须等于图表总数（{len(files)}）")
    return r1, r2, r3


def _split_rows(items: list, rows: tuple[int, int, int]) -> list[list]:
    """按 r1/r2/r3 把有序列表切成最多 3 行（跳过为 0 的行）。"""
    out: list[list] = []
    idx = 0
    for r in rows:
        if r > 0:
            out.append(items[idx : idx + r])
            idx += r
    return out


# ---------------------------------------------------------------------------
# PNG（Pillow）
# ---------------------------------------------------------------------------

def _png_on_white(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGBA")
    background = Image.new("RGBA", img.size, (255, 255, 255, 255))
    background.alpha_composite(img)
    return background.convert("RGB")


def _stitch_png(files: list[tuple[str, bytes]], rows: tuple[int, int, int]) -> bytes:
    try:
        images = [_png_on_white(data) for _, data in files]
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"无法解析 PNG 图片：{exc}") from exc

    grid = _split_rows(images, rows)

    # 每一行：统一缩放到该行最大高度后水平拼接
    row_canvases: list[Image.Image] = []
    for line in grid:
        row_h = max(img.height for img in line)
        scaled: list[Image.Image] = []
        for img in line:
            if img.height != row_h:
                new_w = max(1, round(img.width * row_h / img.height))
                img = img.resize((new_w, row_h), Image.Resampling.LANCZOS)
            scaled.append(img)
        row_w = sum(img.width for img in scaled)
        canvas = Image.new("RGB", (row_w, row_h), (255, 255, 255))
        x = 0
        for img in scaled:
            canvas.paste(img, (x, 0))
            x += img.width
        row_canvases.append(canvas)

    # 各行按最大行宽居中、垂直堆叠
    total_w = max(canvas.width for canvas in row_canvases)
    total_h = sum(canvas.height for canvas in row_canvases)
    result = Image.new("RGB", (total_w, total_h), (255, 255, 255))
    y = 0
    for canvas in row_canvases:
        x = (total_w - canvas.width) // 2
        result.paste(canvas, (x, y))
        y += canvas.height

    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# PDF（PyMuPDF / fitz）
# ---------------------------------------------------------------------------

def _stitch_pdf(files: list[tuple[str, bytes]], rows: tuple[int, int, int]) -> bytes:
    try:
        docs = [fitz.open(stream=data, filetype="pdf") for _, data in files]
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"无法解析 PDF：{exc}") from exc

    try:
        rects = [doc[0].rect for doc in docs]
        grid = _split_rows(list(zip(docs, rects)), rows)

        # 每行：缩放到统一高度（该行最大高度），统计缩放后宽度
        row_layouts: list[dict] = []
        for line in grid:
            row_h = max(rect.height for _, rect in line)
            cells = []
            row_w = 0.0
            for doc, rect in line:
                scale = row_h / rect.height if rect.height else 1.0
                w = rect.width * scale
                cells.append({"doc": doc, "width": w, "height": row_h})
                row_w += w
            row_layouts.append({"cells": cells, "width": row_w, "height": row_h})

        total_w = max(layout["width"] for layout in row_layouts)
        total_h = sum(layout["height"] for layout in row_layouts)

        new_doc = fitz.open()
        page = new_doc.new_page(width=total_w, height=total_h)
        y = 0.0
        for layout in row_layouts:
            x = (total_w - layout["width"]) / 2.0
            for cell in layout["cells"]:
                target = fitz.Rect(x, y, x + cell["width"], y + cell["height"])
                page.show_pdf_page(target, cell["doc"], 0)
                x += cell["width"]
            y += layout["height"]

        return new_doc.tobytes()
    finally:
        for doc in docs:
            doc.close()


# ---------------------------------------------------------------------------
# SVG（svgutils）
# ---------------------------------------------------------------------------

_UNIT_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([a-z%]*)\s*$", re.IGNORECASE)
# pt -> px 近似换算（96dpi / 72pt）
_PT_TO_PX = 96.0 / 72.0


def _parse_length(value, default: float | None = None) -> float | None:
    """把可能带单位（px/pt/...）的 SVG 尺寸解析为像素数值。失败返回 default。"""
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    match = _UNIT_RE.match(text)
    if not match:
        return default
    number = float(match.group(1))
    unit = match.group(2).lower()
    if unit == "pt":
        number *= _PT_TO_PX
    elif unit in ("", "px"):
        pass
    elif unit == "%":
        # 百分比无法独立确定绝对尺寸，交给调用方回退 viewBox
        return default
    # 其余单位（mm/cm/in/em）较少出现，按原值返回避免崩溃
    return number


def _svg_size(fig) -> tuple[float, float]:
    """读取 SVG 宽高（像素）。get_size 不可靠时回退 viewBox。"""
    width = height = None
    try:
        w_raw, h_raw = fig.get_size()
        width = _parse_length(w_raw)
        height = _parse_length(h_raw)
    except Exception:  # noqa: BLE001
        width = height = None

    if width is None or height is None or width <= 0 or height <= 0:
        viewbox = fig.root.get("viewBox") or fig.root.get("viewbox")
        if viewbox:
            parts = re.split(r"[\s,]+", viewbox.strip())
            if len(parts) == 4:
                try:
                    vb_w = float(parts[2])
                    vb_h = float(parts[3])
                    if vb_w > 0 and vb_h > 0:
                        width = vb_w
                        height = vb_h
                except ValueError:
                    pass

    if not width or not height or width <= 0 or height <= 0:
        raise ValueError("无法确定 SVG 尺寸（缺少 width/height 与 viewBox）")
    return float(width), float(height)


def _place_root(root, x: float, y: float, scale: float) -> None:
    """把一个 SVG 子图缩放并平移到 (x, y)，兼容 svgutils 不同版本的 moveto 签名。"""
    try:
        # 新版：moveto(x, y, scale_x=, scale_y=)
        root.moveto(x, y, scale_x=scale, scale_y=scale)
        return
    except TypeError:
        pass
    try:
        # 旧版：moveto(x, y, scale=)
        root.moveto(x, y, scale=scale)
        return
    except TypeError:
        pass
    # 最保守：先缩放（若支持）再平移
    if abs(scale - 1.0) > 1e-6:
        scale_fn = getattr(root, "scale_xy", None) or getattr(root, "scale", None)
        if scale_fn is not None:
            try:
                scale_fn(scale, scale)
            except TypeError:
                scale_fn(scale)
    root.moveto(x, y)


def _stitch_svg(files: list[tuple[str, bytes]], rows: tuple[int, int, int]) -> str:
    try:
        figs = [fromstring(data.decode("utf-8", errors="replace")) for _, data in files]
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"无法解析 SVG：{exc}") from exc

    sizes = [_svg_size(fig) for fig in figs]
    items = list(zip(figs, sizes))
    grid = _split_rows(items, rows)

    # 每行：缩放到统一高度（该行最大高度）
    row_layouts: list[dict] = []
    for line in grid:
        row_h = max(h for _, (_, h) in line)
        cells = []
        row_w = 0.0
        for fig, (w, h) in line:
            scale = row_h / h if h else 1.0
            cells.append({"fig": fig, "width": w * scale, "scale": scale})
            row_w += w * scale
        row_layouts.append({"cells": cells, "width": row_w, "height": row_h})

    total_w = max(layout["width"] for layout in row_layouts)
    total_h = sum(layout["height"] for layout in row_layouts)

    roots = []
    y = 0.0
    for layout in row_layouts:
        x = (total_w - layout["width"]) / 2.0
        for cell in layout["cells"]:
            root = cell["fig"].getroot()
            _place_root(root, x, y, cell["scale"])
            roots.append(root)
            x += cell["width"]
        y += layout["height"]

    out = SVGFigure()
    out.set_size((f"{total_w}px", f"{total_h}px"))
    out.append(roots)
    result = out.to_str()
    if isinstance(result, bytes):
        result = result.decode("utf-8", errors="replace")
    return result


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def stitch(files: list[tuple[str, bytes]], rows: list[int], fmt: str) -> bytes:
    """拼接图表并返回字节。SVG 返回 UTF-8 编码的文本字节。"""
    normalized = normalize_plot_format(fmt)
    r1, r2, r3 = _validate(files, rows)
    grid_rows = (r1, r2, r3)

    if normalized == "png":
        return _stitch_png(files, grid_rows)
    if normalized == "pdf":
        return _stitch_pdf(files, grid_rows)
    # svg
    return _stitch_svg(files, grid_rows).encode("utf-8")


def make_preview(files: list[tuple[str, bytes]], rows: list[int], fmt: str) -> tuple[str, str]:
    """返回 (preview_format, preview)。

    - png：拼接 PNG → base64 data URL，preview_format="png"
    - pdf：拼接 PDF 渲染第 0 页 → PNG data URL，preview_format="png"
    - svg：组合后的 SVG 文本，preview_format="svg"
    """
    normalized = normalize_plot_format(fmt)

    if normalized == "png":
        payload = stitch(files, rows, "png")
        b64 = base64.b64encode(payload).decode("ascii")
        return "png", f"data:image/png;base64,{b64}"

    if normalized == "pdf":
        payload = stitch(files, rows, "pdf")
        doc = fitz.open(stream=payload, filetype="pdf")
        try:
            pixmap = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
            png_bytes = pixmap.tobytes("png")
        finally:
            doc.close()
        b64 = base64.b64encode(png_bytes).decode("ascii")
        return "png", f"data:image/png;base64,{b64}"

    # svg：直接返回组合后的 SVG 文本（前端 v-html，避免栅格化）
    svg_text = stitch(files, rows, "svg").decode("utf-8", errors="replace")
    return "svg", svg_text
