from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter

from .base import PALETTE, configure_matplotlib, empty_figure, figure_to_svg


def build_figure(survival_data_path: str, p_value: float | None = None) -> plt.Figure:
    df = pd.read_parquet(survival_data_path)
    if df.empty:
        return empty_figure("No matched clinical samples available.", "Survival Curve")

    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(9, 6))
    kmf = KaplanMeierFitter()

    for index, cluster_id in enumerate(sorted(df["Cluster"].unique())):
        subset = df[df["Cluster"] == cluster_id]
        if subset.empty:
            continue
        color = PALETTE[index % len(PALETTE)]
        kmf.fit(subset["OS.time"], event_observed=subset["OS"], label=f"Cluster {cluster_id}")
        kmf.plot(ax=ax, ci_show=False, color=color, linewidth=2.5, show_censors=False)

        censored = subset[subset["OS"] == 0]
        if not censored.empty:
            probs = kmf.survival_function_at_times(censored["OS.time"]).to_numpy()
            ax.scatter(
                censored["OS.time"],
                probs,
                marker="+",
                s=80,
                color=color,
                linewidths=2,
                zorder=3,
            )

    if p_value is not None and np.isfinite(p_value):
        ax.text(
            0.05,
            0.06,
            f"P-value: {p_value:.2e}",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            bbox={"facecolor": "white", "edgecolor": "#D6D6D6", "boxstyle": "round,pad=0.5", "alpha": 0.9},
        )

    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Survival Probability")
    legend = ax.legend(
        title="Clusters",
        loc="upper right",
        frameon=True,
        framealpha=0.9,
        facecolor="white",
        edgecolor="black",
        bbox_to_anchor=(1, 1),
    )
    legend.get_title().set_fontweight("bold")
    for text in legend.get_texts():
        text.set_fontweight("bold")
    fig.tight_layout()
    return fig


def render_svg(survival_data_path: str, p_value: float | None = None) -> str:
    return figure_to_svg(build_figure(survival_data_path, p_value))
