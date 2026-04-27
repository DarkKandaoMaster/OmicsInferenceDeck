from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import cm
from scipy.interpolate import griddata

from .base import configure_matplotlib, empty_svg, figure_to_svg, set_2d_plot_box


def render_svg(results_path: str, x_param: str, y_param: str | None = None) -> str:
    df = pd.read_parquet(results_path)
    if df.empty or x_param not in df.columns or "score" not in df.columns:
        return empty_svg("No parameter search result available.", "Parameter Sensitivity")

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
        return figure_to_svg(fig)

    data = df[[x_param, y_param, "score"]].dropna().copy()
    if data.empty:
        return empty_svg("No complete 3D parameter combinations available.", "Parameter Sensitivity")

    x = data[x_param].astype(float).to_numpy()
    y = data[y_param].astype(float).to_numpy()
    z = data["score"].astype(float).to_numpy()

    fig = plt.figure(figsize=(9, 6.8))
    ax = fig.add_subplot(111, projection="3d")

    plotted_surface = False
    if len(np.unique(x)) >= 2 and len(np.unique(y)) >= 2 and len(data) >= 4:
        xi = np.linspace(np.min(x), np.max(x), 45)
        yi = np.linspace(np.min(y), np.max(y), 45)
        x_grid, y_grid = np.meshgrid(xi, yi)
        z_grid = griddata((x, y), z, (x_grid, y_grid), method="cubic")
        if np.isnan(z_grid).all():
            z_grid = griddata((x, y), z, (x_grid, y_grid), method="linear")
        if np.isnan(z_grid).any():
            nearest = griddata((x, y), z, (x_grid, y_grid), method="nearest")
            z_grid = np.where(np.isnan(z_grid), nearest, z_grid)
        ax.plot_surface(
            x_grid,
            y_grid,
            z_grid,
            cmap=cm.viridis,
            alpha=0.9,
            linewidth=0.25,
            antialiased=True,
            edgecolor="#666666",
        )
        plotted_surface = True

    if not plotted_surface:
        ax.plot_trisurf(x, y, z, cmap=cm.viridis, alpha=0.9, linewidth=0.35, edgecolor="#666666")

    ax.scatter(x, y, z, color="#111111", s=18, depthshade=False)
    ax.set_xlabel(x_param, labelpad=10)
    ax.set_ylabel(y_param, labelpad=10)
    ax.set_zlabel("-Log10(P-value)", labelpad=10)
    ax.set_title("Parameter Sensitivity Surface")
    ax.set_box_aspect((4, 3, 2.2))
    ax.view_init(elev=28, azim=45)
    fig.tight_layout()
    return figure_to_svg(fig)
