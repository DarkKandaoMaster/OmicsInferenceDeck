import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from adjustText import adjust_text as _adjust_text

from .base import configure_matplotlib, empty_figure, figure_to_svg, finite_max, set_2d_plot_box

_UP_COLOR = "#D7263D"
_DOWN_COLOR = "#1B98E0"
_NS_COLOR = "#BFC5CC"
_GUIDE_COLOR = "#6B6F76"
_LABEL_COLOR = "#1F2329"


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
    ax.set_facecolor("#FAFBFC")
    ax.grid(True, color="#E5E7EB", linewidth=0.6, linestyle="-", zorder=0)
    ax.set_axisbelow(True)

    n_up = int(up.sum())
    n_down = int(down.sum())

    ax.scatter(
        df.loc[other, "logFC"], df.loc[other, "negLog10P"],
        s=12, c=_NS_COLOR, alpha=0.5, linewidths=0, zorder=2, label="NS",
    )
    ax.scatter(
        df.loc[down, "logFC"], df.loc[down, "negLog10P"],
        s=22, c=_DOWN_COLOR, alpha=0.82, linewidths=0, zorder=3,
        label=f"Down ({n_down})",
    )
    ax.scatter(
        df.loc[up, "logFC"], df.loc[up, "negLog10P"],
        s=22, c=_UP_COLOR, alpha=0.82, linewidths=0, zorder=3,
        label=f"Up ({n_up})",
    )

    y_threshold = -np.log10(p_threshold)
    guide_kwargs = dict(color=_GUIDE_COLOR, linestyle="--", linewidth=0.9, alpha=0.7, zorder=1)
    ax.axhline(y_threshold, **guide_kwargs)
    ax.axvline(logfc_threshold, **guide_kwargs)
    ax.axvline(-logfc_threshold, **guide_kwargs)

    top = df.loc[up | down].sort_values(["t_pvalue", "negLog10P"], ascending=[True, False]).head(10)
    texts = []
    for _, row in top.iterrows():
        texts.append(
            ax.text(
                row["logFC"], row["negLog10P"], str(row["gene"]),
                fontsize=9, color=_LABEL_COLOR, fontweight="bold", zorder=5,
            )
        )

    if texts and _adjust_text is not None:
        # Render once so adjustText has a renderer to measure text extents;
        # without it the arrow drawing falls back and warns about FancyArrowPatch.
        fig.canvas.draw()
        _adjust_text(
            texts,
            ax=ax,
            expand_points=(1.3, 1.5),
            expand_text=(1.2, 1.3),
            force_points=(0.4, 0.6),
            force_text=(0.3, 0.5),
            # shrinkA/shrinkB keep the leader line from striking through the
            # label (and the dot) when adjustText falls back to ax.annotate.
            arrowprops=dict(arrowstyle="-", color="#7A7F87", lw=0.6, alpha=0.8, shrinkA=4, shrinkB=2),
        )
    elif texts:
        for t in texts:
            x, y = t.get_position()
            t.set_position((x, y))
            t.set_horizontalalignment("left")
            t.set_verticalalignment("bottom")

    x_abs = finite_max(np.abs(df["logFC"]), default=1.0)
    y_max = finite_max(df["negLog10P"], default=1.0)
    ax.set_xlim(-x_abs * 1.08, x_abs * 1.08)
    ax.set_ylim(0, y_max * 1.12 + 0.1)
    ax.set_xlabel("Log2 Fold Change")
    ax.set_ylabel("-Log10(P-value)")
    comparison = "Cluster vs Others"
    if "comparison" in df.columns and not df["comparison"].dropna().empty:
        comparison = str(df["comparison"].dropna().iloc[0])
    ax.set_title(f"Cluster {cluster_id}: {comparison}")
    for spine_name in ("left", "bottom", "top", "right"):
        ax.spines[spine_name].set_color("#2B2F36")
    set_2d_plot_box(ax)
    legend = ax.legend(
        loc="upper right", frameon=True, facecolor="white",
        edgecolor="#D0D4DA", framealpha=0.95, fontsize=11,
    )
    legend.get_frame().set_linewidth(0.6)
    fig.tight_layout()
    return fig


def render_svg(volcano_path: str, cluster_id: int, logfc_threshold: float = 0.5, p_threshold: float = 0.05) -> str:
    return figure_to_svg(build_figure(volcano_path, cluster_id, logfc_threshold, p_threshold))
