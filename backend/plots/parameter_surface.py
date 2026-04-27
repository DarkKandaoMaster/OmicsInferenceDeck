from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, LinearSegmentedColormap
from scipy.interpolate import griddata

from .base import SURFACE_COLORS, configure_matplotlib, empty_figure, figure_to_svg, set_2d_plot_box


def _maybe_log_axis(values: np.ndarray) -> tuple[np.ndarray, bool]:
    finite = values[np.isfinite(values)]
    if finite.size == 0 or np.any(finite <= 0):
        return values, False
    if float(np.max(finite) / np.min(finite)) < 100:
        return values, False
    return np.log10(values), True


def _format_log_ticks(ax, axis: str, values: np.ndarray) -> None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return
    low = int(np.floor(np.min(finite)))
    high = int(np.ceil(np.max(finite)))
    ticks = list(range(low, high + 1))
    labels = ["1" if tick == 0 else f"1e{tick}" for tick in ticks]
    if axis == "x":
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, fontsize=14, fontweight="bold")
    else:
        ax.set_yticks(ticks)
        ax.set_yticklabels(labels, fontsize=14, fontweight="bold")


def _interpolated_surface(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_pad = 0.1 * (float(np.max(x)) - float(np.min(x)))
    y_pad = 0.1 * (float(np.max(y)) - float(np.min(y)))
    if x_pad == 0:
        x_pad = 0.1
    if y_pad == 0:
        y_pad = 0.1

    x_fine = np.linspace(float(np.min(x)) - x_pad, float(np.max(x)) + x_pad, 50)
    y_fine = np.linspace(float(np.min(y)) - y_pad, float(np.max(y)) + y_pad, 50)
    x_grid, y_grid = np.meshgrid(x_fine, y_fine)

    try:
        from scipy.interpolate import Rbf

        rbf = Rbf(x, y, z, function="thin_plate", smooth=0.1)
        z_grid = rbf(x_grid, y_grid)
    except Exception:
        try:
            z_grid = griddata((x, y), z, (x_grid, y_grid), method="linear")
        except Exception:
            z_grid = griddata((x, y), z, (x_grid, y_grid), method="nearest")
        if np.isnan(z_grid).any():
            nearest = griddata((x, y), z, (x_grid, y_grid), method="nearest")
            z_grid = np.where(np.isnan(z_grid), nearest, z_grid)

    return x_grid, y_grid, z_grid


def build_figure(results_path: str, x_param: str, y_param: str | None = None) -> plt.Figure:
    df = pd.read_parquet(results_path)
    if df.empty or x_param not in df.columns or "score" not in df.columns:
        return empty_figure("No parameter search result available.", "Parameter Sensitivity")

    configure_matplotlib()

    if not y_param or y_param == x_param or y_param not in df.columns:
        grouped = df.groupby(x_param, as_index=False)["score"].max().sort_values(x_param)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(grouped[x_param], grouped["score"], color="#2E86DE", linewidth=2.6, marker="o", markersize=6)
        ax.set_xlabel(x_param)
        ax.set_ylabel("-Log10(P-value)")
        ax.set_title("Parameter Sensitivity")
        set_2d_plot_box(ax)
        ax.grid(True, linestyle="--", alpha=0.28)
        fig.tight_layout()
        return fig

    data = df[[x_param, y_param, "score"]].dropna().copy()
    if data.empty:
        return empty_figure("No complete 3D parameter combinations available.", "Parameter Sensitivity")

    x = data[x_param].astype(float).to_numpy()
    y = data[y_param].astype(float).to_numpy()
    z = data["score"].astype(float).to_numpy()

    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_subplot(111, projection="3d")
    cmap = LinearSegmentedColormap.from_list("custom_teal_purple", SURFACE_COLORS, N=256)

    x_plot, x_is_log = _maybe_log_axis(x)
    y_plot, y_is_log = _maybe_log_axis(y)
    z_min = float(np.nanmin(z)) if not np.all(np.isnan(z)) else 0.0
    z_max = float(np.nanmax(z)) if not np.all(np.isnan(z)) else 1.0
    if z_min == z_max:
        z_min -= 0.1
        z_max += 0.1

    if len(np.unique(x_plot)) >= 2 and len(np.unique(y_plot)) >= 2 and len(data) >= 4:
        x_grid, y_grid, z_grid = _interpolated_surface(x_plot, y_plot, z)
        z_grid = np.nan_to_num(z_grid, nan=0.0)
        surf = ax.plot_surface(
            x_grid,
            y_grid,
            z_grid,
            cmap=cmap,
            alpha=0.9,
            vmin=z_min,
            vmax=z_max,
            linewidth=0.5,
            antialiased=True,
            rstride=1,
            cstride=1,
            shade=True,
            edgecolor="#666666",
        )
        try:
            light = LightSource(azdeg=135, altdeg=30)
            shaded = light.shade(z_grid, cmap=cmap, vert_exag=0.1, blend_mode="hsv", dx=0.3, dy=0.3, fraction=0.8)
            surf.set_facecolor(shaded.reshape(-1, 4))
        except Exception:
            pass
    elif len(data) >= 3:
        ax.plot_trisurf(x_plot, y_plot, z, cmap=cmap, alpha=0.9, linewidth=0.5, edgecolor="#666666")
    else:
        ax.scatter(x_plot, y_plot, z, color="#666666", s=50, depthshade=False)

    ax.set_xlabel(x_param, labelpad=10)
    ax.set_ylabel(y_param, labelpad=10)
    ax.set_zlabel("$-\\log_{10}(p)$", fontsize=12, labelpad=20)
    ax.zaxis.set_rotate_label(True)
    ax.set_box_aspect([1, 1, 0.8])
    ax.view_init(elev=30, azim=60)
    ax.grid(True, linestyle="--", alpha=0.3)
    if x_is_log:
        _format_log_ticks(ax, "x", x_plot)
    if y_is_log:
        _format_log_ticks(ax, "y", y_plot)
    ax.tick_params(axis="z", which="major", labelsize=14, pad=8)
    z_ceil = float(np.ceil(np.nanmax(z))) if np.nanmax(z) > 0 else 1.0
    ax.set_zlim(0, z_ceil)
    plt.subplots_adjust(left=0.25, right=0.9, bottom=0.1, top=0.9)
    fig.tight_layout(rect=[0.25, 0, 0.95, 0.95])
    return fig


def render_svg(results_path: str, x_param: str, y_param: str | None = None) -> str:
    return figure_to_svg(build_figure(results_path, x_param, y_param))
