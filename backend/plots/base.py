import io
import json
import math
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


UPLOAD_ROOT = Path("upload")
CLUSTER_RESULT_FILE = "cluster_result.parquet"
DIFFERENTIAL_VOLCANO_FILE = "differential_volcano.parquet"
DIFFERENTIAL_HEATMAP_FILE = "differential_heatmap.parquet"
DIFFERENTIAL_META_FILE = "differential_meta.json"
SURVIVAL_DATA_FILE = "survival_data.parquet"
PARAMETER_SEARCH_FILE = "parameter_search.parquet"
PARAMETER_SEARCH_META_FILE = "parameter_search_meta.json"

SUPPORTED_PLOT_FORMATS = {"png", "svg", "pdf"}
PLOT_MEDIA_TYPES = {
    "png": "image/png",
    "svg": "image/svg+xml; charset=utf-8",
    "pdf": "application/pdf",
}

PALETTE = [
    "#E41A1C",
    "#377EB8",
    "#4DAF4A",
    "#984EA3",
    "#FF7F00",
    "#A65628",
    "#F781BF",
    "#999999",
    "#66C2A5",
    "#FC8D62",
]

CANAKO_TSNE_RANDOM_STATE = 3407

SURFACE_COLORS = [
    (0.8, 0.9, 0.9),
    (0.7, 0.85, 0.9),
    (0.8, 0.7, 0.9),
    (0.9, 0.7, 0.8),
]


def session_dir(session_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", session_id or ""):
        raise ValueError("Invalid session_id")
    return UPLOAD_ROOT / session_id


def plot_path(session_id: str, filename: str) -> Path:
    return session_dir(session_id) / filename


def enrichment_file(database: str) -> str:
    normalized = database.upper()
    if normalized not in {"GO", "KEGG"}:
        raise ValueError("database must be GO or KEGG")
    return f"enrichment_{normalized}.parquet"


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.weight": "bold",
            "font.size": 16,
            "axes.labelweight": "bold",
            "axes.titleweight": "bold",
            "axes.linewidth": 1.1,
            "xtick.labelsize": 16,
            "ytick.labelsize": 16,
            "legend.fontsize": 16,
            "legend.title_fontsize": 16,
            "svg.fonttype": "none",
        }
    )


def normalize_plot_format(file_format: str) -> str:
    normalized = (file_format or "").lower().strip().lstrip(".")
    if normalized not in SUPPORTED_PLOT_FORMATS:
        raise ValueError("format must be one of: PNG, SVG, PDF")
    return normalized


def media_type_for_format(file_format: str) -> str:
    return PLOT_MEDIA_TYPES[normalize_plot_format(file_format)]


def strip_to_svg(text: str) -> str:
    start = text.find("<svg")
    end = text.rfind("</svg>")
    if start == -1 or end == -1:
        return text.strip()
    return text[start : end + len("</svg>")]


def figure_to_bytes(fig: plt.Figure, file_format: str, dpi: int = 300) -> bytes:
    normalized = normalize_plot_format(file_format)
    buffer = io.BytesIO()
    save_kwargs: dict[str, Any] = {
        "format": normalized,
        "bbox_inches": "tight",
        "facecolor": "white",
    }
    if normalized == "png":
        save_kwargs["dpi"] = dpi

    fig.savefig(buffer, **save_kwargs)
    plt.close(fig)
    payload = buffer.getvalue()
    if normalized == "svg":
        return strip_to_svg(payload.decode("utf-8", errors="replace")).encode("utf-8")
    return payload


def figure_to_svg(fig: plt.Figure) -> str:
    return figure_to_bytes(fig, "svg").decode("utf-8", errors="replace")


def empty_figure(message: str, title: str | None = None) -> plt.Figure:
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.axis("off")
    if title:
        ax.set_title(title, pad=16)
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        transform=ax.transAxes,
        fontsize=14,
        color="#666666",
        wrap=True,
    )
    return fig


def empty_svg(message: str, title: str | None = None) -> str:
    return figure_to_svg(empty_figure(message, title))
    return figure_to_svg(fig)


def set_2d_plot_box(ax: plt.Axes) -> None:
    try:
        ax.set_box_aspect(0.75)
    except Exception:
        pass


def finite_max(values: Iterable[float], default: float = 1.0) -> float:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return default
    return float(np.nanmax(arr))


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return parsed


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_r_svg(script_name: str, args: list[str | os.PathLike[str]], timeout: int = 3600) -> str:
    script_path = Path(__file__).with_name(script_name).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"R plot script not found: {script_path}")

    result = subprocess.run(
        ["Rscript", str(script_path), *[str(arg) for arg in args]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    svg = strip_to_svg(result.stdout)
    if not svg.startswith("<svg"):
        raise RuntimeError(result.stderr.strip() or "R script did not return SVG")
    return svg


def run_r_plot_bytes(
    script_name: str,
    args: list[str | os.PathLike[str] | int | float],
    file_format: str,
    output_dir: Path,
    timeout: int = 3600,
) -> bytes:
    normalized = normalize_plot_format(file_format)
    script_path = Path(__file__).with_name(script_name).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"R plot script not found: {script_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{uuid.uuid4().hex}.{normalized}"
    try:
        result = subprocess.run(
            ["Rscript", str(script_path), *[str(arg) for arg in args], normalized, str(output_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(result.stderr.strip() or "R script did not create plot output")
        return output_path.read_bytes()
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
