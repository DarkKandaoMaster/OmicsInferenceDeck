#运行这个算法会报错：[算法错误] only 0-dimensional arrays can be converted to Python scalars
#之后再来修

import inspect

import numpy as np
import pandas as pd
import pyrea
from .base import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    def fit_predict(self, data: dict[str, pd.DataFrame]) -> tuple[np.ndarray, np.ndarray, list[str]]:

        if len(data) < 2:
            raise ValueError("Parea requires at least two omics views.")

        df_concat = pd.concat(data.values(), axis=1, join="inner")
        sample_names = df_concat.index.astype(str).tolist()
        if len(sample_names) < 2:
            raise ValueError("Parea requires at least two matched samples across omics views.")

        aligned_matrices = []
        for df in data.values():
            aligned_df = df.loc[df_concat.index]
            values = aligned_df.to_numpy(dtype=float)
            if not np.isfinite(values).all():
                raise ValueError("Parea input contains missing or non-finite values.")
            aligned_matrices.append(values)

        n_clusters = int(self.params.get("n_clusters", 3))
        if n_clusters < 2:
            raise ValueError("Parea requires n_clusters >= 2.")
        if n_clusters >= len(sample_names):
            raise ValueError("Parea requires n_clusters to be smaller than the number of matched samples.")

        random_state = self.params.get("random_state")
        if random_state is not None:
            np.random.seed(int(random_state))

        # DarkKandaoMaster: Parea is exposed through the Pyrea package; default to Parea 2.
        structure = str(self.params.get("parea_structure", "2"))
        labels = self._run_parea(pyrea, aligned_matrices, n_clusters, structure)
        labels = np.asarray(labels, dtype=int)

        if labels.ndim != 1:
            raise ValueError("Parea returned labels with an invalid shape.")
        if labels.shape[0] != len(sample_names):
            raise ValueError("Parea returned a label count that does not match the sample count.")

        return labels, df_concat.to_numpy(dtype=float), sample_names

    def _run_parea(
        self,
        pyrea_module,
        views: list[np.ndarray],
        n_clusters: int,
        structure: str,
    ) -> list[int] | np.ndarray:
        if structure == "2" and hasattr(pyrea_module, "parea_2_mv"):
            n_views = len(views)
            methods = self._hierarchical_methods(n_views)
            return pyrea_module.parea_2_mv(
                views,
                clusterers=["hierarchical"] * n_views,
                methods=methods,
                k_s=[n_clusters] * n_views,
                precomputed_clusterers=["hierarchical"] * n_views,
                precomputed_methods=methods,
                precomputed_k_s=[n_clusters] * n_views,
                fusion_method="disagreement",
                k_final=n_clusters,
            )

        helper = getattr(pyrea_module, f"parea_{structure}", None)
        if helper is None:
            raise RuntimeError(f"Pyrea does not provide parea_{structure}().")
        if structure == "2" and len(views) != 3:
            raise ValueError("This Pyrea version requires exactly three omics views for parea_2().")

        kwargs = self._cluster_count_kwargs(helper, n_clusters)
        try:
            return helper(views, **kwargs)
        except TypeError as exc:
            if not kwargs:
                raise
            try:
                return helper(views)
            except TypeError:
                raise exc

    def _cluster_count_kwargs(self, helper, n_clusters: int) -> dict[str, int]:
        try:
            signature = inspect.signature(helper)
        except (TypeError, ValueError):
            return {"k_final": n_clusters}

        params = signature.parameters
        if "k_final" in params:
            return {"k_final": n_clusters}
        if "k" in params:
            return {"k": n_clusters}
        return {}

    def _hierarchical_methods(self, n_views: int) -> list[str]:
        base_methods = ["ward", "complete", "single"]
        return [base_methods[i % len(base_methods)] for i in range(n_views)]
