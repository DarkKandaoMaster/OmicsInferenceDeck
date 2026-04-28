import inspect

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

import umap
import seaborn as sns

from .base import CANAKO_TSNE_RANDOM_STATE, PALETTE, configure_matplotlib, empty_figure, figure_to_svg


def _scatter_palette(n_colors: int):
    if sns is not None:
        return sns.color_palette("husl", n_colors)
    return [PALETTE[index % len(PALETTE)] for index in range(n_colors)]


def _tsne_kwargs(n_samples: int) -> dict:
    kwargs = {
        "n_components": 2,
        "perplexity": min(50, n_samples - 1),
        "learning_rate": "auto",
        "early_exaggeration": 50,
        "init": "random",
        "random_state": CANAKO_TSNE_RANDOM_STATE,
        "method": "exact",
    }
    iteration_arg = "max_iter" if "max_iter" in inspect.signature(TSNE).parameters else "n_iter"
    kwargs[iteration_arg] = 1000
    return kwargs


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
        return TSNE(**_tsne_kwargs(n_samples)).fit_transform(embeddings)

    if umap is None:
        return _coords(embeddings, "PCA", random_state)
    return umap.UMAP(n_components=2, random_state=random_state).fit_transform(embeddings)


def build_figure(cluster_result_path: str, reduction: str = "PCA", random_state: int | None = 42) -> plt.Figure:
    df = pd.read_parquet(cluster_result_path)
    if df.empty:
        return empty_figure("No clustering result available.", "Cluster Scatter")

    emb_cols = [col for col in df.columns if col.startswith("emb_")]
    if len(emb_cols) == 0:
        return empty_figure("No feature matrix columns found in cluster_result.parquet.", "Cluster Scatter")

    labels = df["label"].to_numpy()
    embeddings = df[emb_cols].to_numpy(dtype=float)
    coords = _coords(embeddings, reduction, random_state)

    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(12, 10))
    unique_labels = sorted(pd.Series(labels).dropna().unique())
    palette = _scatter_palette(len(unique_labels))

    for index, label in enumerate(unique_labels):
        mask = labels == label
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            label=f"Cluster {label}",
            s=50,
            color=palette[index],
            alpha=0.7,
            linewidths=0,
        )

    axis_prefix = {"PCA": "PC", "t-SNE": "t-SNE", "UMAP": "UMAP"}.get(reduction, "Dim")
    if reduction == "t-SNE":
        ax.set_xlabel("t-SNE dimension 1")
        ax.set_ylabel("t-SNE dimension 2")
    else:
        ax.set_xlabel(f"{axis_prefix} 1")
        ax.set_ylabel(f"{axis_prefix} 2")
    ax.set_title(f"Sample Clustering ({reduction})")
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
    legend.get_title().set_fontweight("bold")
    for text in legend.get_texts():
        text.set_fontweight("bold")
    fig.tight_layout()
    return fig


def render_svg(cluster_result_path: str, reduction: str = "PCA", random_state: int | None = 42) -> str:
    return figure_to_svg(build_figure(cluster_result_path, reduction, random_state))
