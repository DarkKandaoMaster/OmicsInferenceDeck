from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .base import configure_matplotlib, empty_figure, figure_to_svg, finite_max, set_2d_plot_box


def build_figure(
    volcano_path: str,
    cluster_id: int,
    logfc_threshold: float = 0.5,
    p_threshold: float = 0.05,
) -> plt.Figure:
    df = pd.read_parquet(volcano_path)
    df = df[df["cluster"].astype(int) == int(cluster_id)].copy()
    if df.empty:
        return empty_figure(f"No differential result for Cluster {cluster_id}.", "Differential Volcano")

    df["t_pvalue"] = pd.to_numeric(df["t_pvalue"], errors="coerce").fillna(1.0)
    df["logFC"] = pd.to_numeric(df["logFC"], errors="coerce").fillna(0.0)
    df["negLog10P"] = pd.to_numeric(df["negLog10P"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)

    up = (df["t_pvalue"] < p_threshold) & (df["logFC"] > logfc_threshold)
    down = (df["t_pvalue"] < p_threshold) & (df["logFC"] < -logfc_threshold)
    other = ~(up | down)

    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df.loc[other, "logFC"], df.loc[other, "negLog10P"], s=14, c="#C9CDD3", alpha=0.55, linewidths=0)
    ax.scatter(df.loc[down, "logFC"], df.loc[down, "negLog10P"], s=20, c="#2E86DE", alpha=0.78, linewidths=0, label="Down")
    ax.scatter(df.loc[up, "logFC"], df.loc[up, "negLog10P"], s=20, c="#E74C3C", alpha=0.78, linewidths=0, label="Up")

    y_threshold = -np.log10(p_threshold)
    ax.axhline(y_threshold, color="#555555", linestyle="--", linewidth=1.0)
    ax.axvline(logfc_threshold, color="#555555", linestyle="--", linewidth=1.0)
    ax.axvline(-logfc_threshold, color="#555555", linestyle="--", linewidth=1.0)

    top = df.loc[up | down].sort_values(["t_pvalue", "negLog10P"], ascending=[True, False]).head(8)
    for _, row in top.iterrows():
        ax.annotate(
            str(row["gene"]),
            (row["logFC"], row["negLog10P"]),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=8,
            color="#222222",
        )

    x_abs = finite_max(np.abs(df["logFC"]), default=1.0)
    y_max = finite_max(df["negLog10P"], default=1.0)
    ax.set_xlim(-x_abs * 1.08, x_abs * 1.08)
    ax.set_ylim(0, y_max * 1.12 + 0.1)
    ax.set_xlabel("Log2 Fold Change")
    ax.set_ylabel("-Log10(P-value)")
    ax.set_title(f"Cluster {cluster_id} vs Others")
    set_2d_plot_box(ax)
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#222222")
    fig.tight_layout()
    return fig


def render_svg(volcano_path: str, cluster_id: int, logfc_threshold: float = 0.5, p_threshold: float = 0.05) -> str:
    return figure_to_svg(build_figure(volcano_path, cluster_id, logfc_threshold, p_threshold))
