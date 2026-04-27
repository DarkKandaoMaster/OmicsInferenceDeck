from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter

from .base import PALETTE, configure_matplotlib, empty_svg, figure_to_svg, set_2d_plot_box


def render_svg(survival_data_path: str, p_value: float | None = None) -> str:
    df = pd.read_parquet(survival_data_path)
    if df.empty:
        return empty_svg("No matched clinical samples available.", "Survival Curve")

    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 6))
    kmf = KaplanMeierFitter()

    for index, cluster_id in enumerate(sorted(df["Cluster"].unique())):
        subset = df[df["Cluster"] == cluster_id]
        if subset.empty:
            continue
        color = PALETTE[index % len(PALETTE)]
        kmf.fit(subset["OS.time"], event_observed=subset["OS"], label=f"Cluster {cluster_id}")
        kmf.plot(ax=ax, ci_show=False, color=color, linewidth=2.4, show_censors=False)

        censored = subset[subset["OS"] == 0]
        if not censored.empty:
            probs = kmf.survival_function_at_times(censored["OS.time"]).to_numpy()
            ax.scatter(
                censored["OS.time"],
                probs,
                marker="+",
                s=70,
                color=color,
                linewidths=1.8,
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
            bbox={"facecolor": "white", "edgecolor": "#D6D6D6", "boxstyle": "round,pad=0.35", "alpha": 0.92},
            fontsize=12,
        )

    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Survival Probability")
    ax.set_ylim(-0.02, 1.03)
    ax.set_xlim(left=0)
    ax.set_title("Kaplan-Meier Survival Curve")
    set_2d_plot_box(ax)
    ax.legend(title="Clusters", loc="upper right", frameon=True, facecolor="white", edgecolor="#222222")
    fig.tight_layout()
    return figure_to_svg(fig)
