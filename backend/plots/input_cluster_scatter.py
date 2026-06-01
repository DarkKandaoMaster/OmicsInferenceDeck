"""聚类前的输入空间散点图。

读取原始多模态组学数据，按 cluster_result.parquet 的样本顺序对齐，
每个模态独立 StandardScaler 标准化，沿特征轴横向拼接成单一矩阵，
再用 t-SNE / PCA / UMAP 降维到 2D。颜色仍使用算法预测出的 label，
用以观察输入空间里相同标签是否已经天然成簇。
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

from routers.upload import OMICS_DATA_FILE, load_frame_dict

from .base import (
    CLUSTER_RESULT_FILE,
    configure_matplotlib,
    empty_figure,
    figure_to_svg,
    plot_path,
    reference_font_dict,
)
from .cluster_scatter import _coords, _scatter_palette


PLOT_TITLE = "Input Cluster Scatter"


def _build_input_matrix(omics_path: str, sample_order: list) -> np.ndarray | None:
    try:
        omics = load_frame_dict(omics_path)
    except Exception:
        return None
    if not omics:
        return None

    blocks: list[np.ndarray] = []
    for _, frame in omics.items():
        aligned = frame.reindex(sample_order)
        numeric = aligned.apply(pd.to_numeric, errors="coerce")
        numeric = numeric.dropna(axis=1, how="all")
        if numeric.shape[1] == 0:
            continue
        # column-wise mean impute so StandardScaler doesn't blow up on NaN
        col_mean = numeric.mean(axis=0)
        numeric = numeric.fillna(col_mean).fillna(0.0)
        scaled = StandardScaler().fit_transform(numeric.to_numpy(dtype=float))
        blocks.append(scaled)

    if not blocks:
        return None
    return np.concatenate(blocks, axis=1)


def build_figure(
    omics_path: str,
    cluster_result_path: str,
    reduction: str = "t-SNE",
    random_state: int | None = 42,
) -> plt.Figure:
    if not Path(cluster_result_path).exists():
        return empty_figure("cluster_result.parquet not found.", PLOT_TITLE)
    if not Path(omics_path).exists():
        return empty_figure("omics_data.parquet not found.", PLOT_TITLE)

    df = pd.read_parquet(cluster_result_path)
    if df.empty or "label" not in df.columns:
        return empty_figure("No clustering result available.", PLOT_TITLE)

    if "sample_name" in df.columns:
        sample_order = df["sample_name"].astype(str).tolist()
    else:
        sample_order = [str(idx) for idx in df.index.tolist()]
    labels = df["label"].to_numpy()

    X = _build_input_matrix(omics_path, sample_order)
    if X is None or X.shape[0] == 0 or X.shape[1] == 0:
        return empty_figure("No omics features available for input scatter.", PLOT_TITLE)
    if X.shape[0] != len(labels):
        return empty_figure("Omics samples and cluster labels are not aligned.", PLOT_TITLE)

    coords = _coords(X, reduction, random_state)

    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(12, 10))
    unique_labels = sorted(pd.Series(labels).dropna().unique())
    palette = _scatter_palette(max(len(unique_labels), 1))
    label_font = reference_font_dict()
    tick_font = reference_font_dict()

    for label in unique_labels:
        mask = labels == label
        try:
            color_index = int(label) % len(palette)
        except (TypeError, ValueError):
            color_index = unique_labels.index(label) % len(palette)
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            label=f"Cluster {label}",
            s=50,
            color=palette[color_index],
            alpha=0.7,
        )

    axis_prefix = {"PCA": "PC", "t-SNE": "t-SNE", "UMAP": "UMAP"}.get(reduction, "Dim")
    if reduction == "t-SNE":
        ax.set_xlabel("t-SNE dimension 1", fontproperties=label_font)
        ax.set_ylabel("t-SNE dimension 2", fontproperties=label_font)
    else:
        ax.set_xlabel(f"{axis_prefix} 1", fontproperties=label_font)
        ax.set_ylabel(f"{axis_prefix} 2", fontproperties=label_font)

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

    ax.set_title(f"Input Data {reduction}", fontdict=label_font)
    ax.grid(False)
    legend = ax.legend(
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
    return fig


def render_svg(
    omics_path: str,
    cluster_result_path: str,
    reduction: str = "t-SNE",
    random_state: int | None = 42,
) -> str:
    return figure_to_svg(build_figure(omics_path, cluster_result_path, reduction, random_state))
