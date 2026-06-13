"""生物标志物簇散点图（还原 B 图）。

把全部样本铺在同一张全局 t-SNE 上：形状区分所属簇，颜色表示某个标志基因的
z-score 表达。基因由「该簇排名第一的显著标志基因」决定，规则与 differential.R
中的 top_significant_genes 一致。
"""

import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .base import (
    configure_matplotlib,
    empty_figure,
    figure_to_svg,
    reference_font_dict,
)
from .pred_cluster_scatter import _coords

# 前四个 marker 对应 B 图的 ●▲■＋，后面追加更多可区分形状，按簇序循环。
_MARKERS = ["o", "^", "s", "+", "D", "v"]


def _sample_prefix(sample_name: str) -> str:
    """与 routers/differential.py 一致的样本前缀回退匹配（兼容表达矩阵模式）。"""
    parts = re.split(r"[-.]", str(sample_name))
    if len(parts) >= 3:
        return "-".join(parts[:3])
    return str(sample_name)


def resolve_top_gene(volcano_path: str, cluster_id: int) -> str | None:
    """复刻 differential.R 的 top_significant_genes 规则，取该簇排名第一的基因。"""
    df = pd.read_parquet(volcano_path)
    if df.empty or "cluster" not in df.columns or "gene" not in df.columns:
        return None

    subset = df[df["cluster"] == cluster_id].copy()
    if subset.empty:
        return None

    subset = subset[(subset["FDR"] < 0.05) & (subset["logFC"].abs() >= 0.5)]
    if subset.empty:
        return None

    subset["_abs_logfc"] = subset["logFC"].abs()
    subset = subset.sort_values(by=["FDR", "_abs_logfc"], ascending=[True, False])
    return str(subset.iloc[0]["gene"])


def _zscore_lookup(heatmap_path: str, gene: str) -> dict[str, float] | None:
    """从 heatmap parquet 取 sample_name -> 该基因 z-score 的映射。"""
    df = pd.read_parquet(heatmap_path)
    if df.empty or "sample_name" not in df.columns or gene not in df.columns:
        return None
    values = pd.to_numeric(df[gene], errors="coerce")
    return {
        str(name): float(value)
        for name, value in zip(df["sample_name"], values)
        if pd.notna(value)
    }


def build_figure(
    cluster_result_path: str,
    heatmap_path: str,
    volcano_path: str,
    cluster_id: int,
    reduction: str = "t-SNE",
    random_state: int | None = None,
) -> tuple[plt.Figure, str | None]:
    df = pd.read_parquet(cluster_result_path)
    if df.empty:
        return empty_figure("No clustering result available.", "Biomarker Cluster Scatter"), None

    emb_cols = [col for col in df.columns if col.startswith("emb_")]
    if len(emb_cols) == 0:
        return empty_figure("未检测到融合后的特征矩阵，无法绘制生物标志物簇散点图。", "Biomarker Cluster Scatter"), None

    gene = resolve_top_gene(volcano_path, cluster_id)
    if gene is None:
        return empty_figure(f"Cluster {cluster_id} 无显著标志基因", "Biomarker Cluster Scatter"), None

    lookup = _zscore_lookup(heatmap_path, gene)
    if not lookup:
        return empty_figure(f"差异热图中未找到基因 {gene} 的表达值。", "Biomarker Cluster Scatter"), gene

    # 全局降维坐标（全部样本，seed 固定 3407，与 A 图同一景观）。
    embeddings = df[emb_cols].to_numpy(dtype=float)
    coords = _coords(embeddings, reduction, random_state)

    sample_names = df["sample_name"].astype(str).to_numpy()
    labels = df["label"].to_numpy()

    # 前缀回退映射，兼容 tumor-vs-normal 表达矩阵模式（ID 体系不同）。
    prefix_lookup: dict[str, float] = {}
    for name, value in lookup.items():
        prefix_lookup.setdefault(_sample_prefix(name), value)

    zscores = np.full(len(sample_names), np.nan, dtype=float)
    for index, name in enumerate(sample_names):
        if name in lookup:
            zscores[index] = lookup[name]
        else:
            fallback = prefix_lookup.get(_sample_prefix(name))
            if fallback is not None:
                zscores[index] = fallback

    valid = np.isfinite(zscores)
    if not valid.any():
        return empty_figure(f"没有样本能匹配到基因 {gene} 的 z-score。", "Biomarker Cluster Scatter"), gene

    coords = coords[valid]
    labels = labels[valid]
    zscores = zscores[valid]

    # 对称稳健色标：±max(|q02|, |q98|)，所有簇共享同一色标。
    q02, q98 = np.quantile(zscores, [0.02, 0.98])
    bound = max(abs(float(q02)), abs(float(q98)), 1e-6)
    vmin, vmax = -bound, bound

    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_box_aspect(0.75)
    label_font = reference_font_dict()
    tick_font = reference_font_dict()

    unique_labels = sorted(pd.Series(labels).dropna().unique())
    scatter = None
    for index, label in enumerate(unique_labels):
        mask = labels == label
        scatter = ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            c=zscores[mask],
            cmap="RdYlBu_r",
            vmin=vmin,
            vmax=vmax,
            marker=_MARKERS[index % len(_MARKERS)],
            s=60,
            alpha=0.85,
        )

    axis_prefix = {"PCA": "PC", "t-SNE": "t-SNE", "UMAP": "UMAP"}.get(reduction, "Dim")
    ax.set_xlabel(f"{axis_prefix}1", fontproperties=label_font)
    ax.set_ylabel(f"{axis_prefix}2", fontproperties=label_font)
    ax.set_title(f"{gene}(cluster{cluster_id})", fontdict=label_font)
    ax.grid(False)
    plt.setp(
        ax.get_xticklabels(),
        fontname=tick_font["family"],
        fontsize=tick_font["size"],
        fontweight=tick_font["weight"],
    )
    plt.setp(
        ax.get_yticklabels(),
        fontname=tick_font["family"],
        fontsize=tick_font["size"],
        fontweight=tick_font["weight"],
    )

    # 颜色条：表达 z-score。横向放置在右上角图例下方。
    cax = ax.inset_axes([0.84, 0.69, 0.15, 0.025])
    colorbar = fig.colorbar(scatter, cax=cax, orientation="horizontal")
    colorbar.set_label("z-score", fontproperties=label_font)
    colorbar.outline.set_visible(False)
    cax.xaxis.set_ticks_position("bottom")
    cax.xaxis.set_label_position("top")
    for text in colorbar.ax.get_xticklabels():
        text.set_fontproperties(label_font)

    # 形状图例：中性色 proxy handles，仅表达「形状=簇」，避免与颜色语义冲突。
    handles = [
        Line2D(
            [0],
            [0],
            marker=_MARKERS[index % len(_MARKERS)],
            color="#555555",
            linestyle="none",
            markersize=9,
            markerfacecolor="#555555" if _MARKERS[index % len(_MARKERS)] != "+" else "none",
        )
        for index, label in enumerate(unique_labels)
    ]
    legend = ax.legend(
        handles,
        [f"cluster={label}" for label in unique_labels],
        title="Clusters",
        loc="upper right",
        frameon=True,
        framealpha=0.9,
        facecolor="white",
        edgecolor="black",
        bbox_to_anchor=(1, 1),
    )
    plt.setp(legend.get_title(), fontproperties=label_font)
    for text in legend.get_texts():
        text.set_fontproperties(label_font)

    fig.tight_layout()
    return fig, gene


def render_svg(
    cluster_result_path: str,
    heatmap_path: str,
    volcano_path: str,
    cluster_id: int,
    reduction: str = "t-SNE",
    random_state: int | None = None,
) -> tuple[str, str | None]:
    fig, gene = build_figure(cluster_result_path, heatmap_path, volcano_path, cluster_id, reduction, random_state)
    return figure_to_svg(fig), gene
