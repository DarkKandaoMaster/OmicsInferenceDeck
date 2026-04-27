from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

try:
    import umap
except Exception:  # pragma: no cover - optional import failure is handled at runtime.
    umap = None

from .base import PALETTE, configure_matplotlib, empty_svg, figure_to_svg, set_2d_plot_box


def _coords(embeddings: np.ndarray, reduction: str, random_state: int | None) -> np.ndarray:
    n_samples = embeddings.shape[0]
    if n_samples == 0:
        return np.empty((0, 2))
    if n_samples == 1:
        return np.array([[0.0, 0.0]])

    if reduction == "PCA":
        n_components = min(2, embeddings.shape[1], n_samples)
        coords = PCA(n_components=n_components, random_state=random_state).fit_transform(embeddings)
        if coords.shape[1] == 1:
            coords = np.column_stack([coords[:, 0], np.zeros(n_samples)])
        return coords

    if reduction == "t-SNE":
        if n_samples < 4:
            return _coords(embeddings, "PCA", random_state)
        perplexity = min(50, max(2, (n_samples - 1) // 3))
        perplexity = min(perplexity, n_samples - 1)
        return TSNE(
            n_components=2,
            perplexity=perplexity,
            learning_rate="auto",
            init="random",
            random_state=random_state,
            method="barnes_hut",
        ).fit_transform(embeddings)

    if umap is None:
        return _coords(embeddings, "PCA", random_state)
    return umap.UMAP(n_components=2, random_state=random_state).fit_transform(embeddings)


def render_svg(cluster_result_path: str, reduction: str = "PCA", random_state: int | None = 42) -> str:
    df = pd.read_parquet(cluster_result_path)
    if df.empty:
        return empty_svg("No clustering result available.", "Cluster Scatter")

    emb_cols = [col for col in df.columns if col.startswith("emb_")]
    if len(emb_cols) == 0:
        return empty_svg("No feature matrix columns found in cluster_result.parquet.", "Cluster Scatter")

    labels = df["label"].to_numpy()
    embeddings = df[emb_cols].to_numpy(dtype=float)
    coords = _coords(embeddings, reduction, random_state)

    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 6))
    unique_labels = sorted(pd.Series(labels).dropna().unique())

    for index, label in enumerate(unique_labels):
        mask = labels == label
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            label=f"Cluster {label}",
            s=48,
            color=PALETTE[index % len(PALETTE)],
            alpha=0.78,
            edgecolors="black",
            linewidths=0.35,
        )

    axis_prefix = {"PCA": "PC", "t-SNE": "t-SNE", "UMAP": "UMAP"}.get(reduction, "Dim")
    ax.set_xlabel(f"{axis_prefix} 1")
    ax.set_ylabel(f"{axis_prefix} 2")
    ax.set_title(f"Sample Clustering ({reduction})")
    set_2d_plot_box(ax)
    ax.grid(False)
    ax.legend(title="Clusters", loc="upper right", frameon=True, facecolor="white", edgecolor="#222222")
    fig.tight_layout()
    return figure_to_svg(fig)
