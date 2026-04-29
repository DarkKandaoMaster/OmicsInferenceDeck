import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from .base import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    def fit_predict(self, data: dict[str, pd.DataFrame]) -> tuple[np.ndarray, np.ndarray, list[str]]:
        omics_path = self.params.get("omics_path")
        if not omics_path:
            raise ValueError("PIntMF requires omics_path so R can read the saved omics_data.parquet directly.")

        input_path = Path(omics_path)
        if not input_path.exists():
            raise FileNotFoundError(f"PIntMF input file not found: {input_path}")

        script_path = Path(__file__).with_suffix(".R")
        if not script_path.exists():
            raise FileNotFoundError(f"PIntMF R script not found: {script_path}")

        n_clusters = int(self.params.get("n_clusters", 3))
        latent_dim = int(self.params.get("latent_dim", n_clusters))
        max_it = int(self.params.get("pintmf_max_iter", self.params.get("max_it", 20)))
        init_flavor = str(self.params.get("init_flavor", "snf"))
        flavor_mod = str(self.params.get("flavor_mod", "glmnet"))
        flavor_mod_w = str(self.params.get("flavor_mod_w", "glmnet"))
        random_state = self.params.get("random_state")
        seed_arg = "" if random_state is None else str(int(random_state))

        result = subprocess.run(
            [
                "Rscript",
                str(script_path),
                str(input_path),
                str(n_clusters),
                str(latent_dim),
                str(max_it),
                seed_arg,
                init_flavor,
                flavor_mod,
                flavor_mod_w,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(self.params.get("timeout", 3600)),
        )

        payload = self._parse_r_output(result)

        sample_names = [str(sample) for sample in payload.get("sample_names", [])]
        labels = np.asarray(payload.get("labels", []), dtype=int)
        embeddings = np.asarray(payload.get("embeddings", []), dtype=float)

        if labels.ndim != 1:
            raise ValueError("PIntMF returned labels with an invalid shape.")
        if embeddings.ndim != 2 or embeddings.shape[1] < 1:
            raise ValueError("PIntMF returned embeddings with an invalid shape.")
        if len(sample_names) != len(labels) or embeddings.shape[0] != len(labels):
            raise ValueError("PIntMF returned inconsistent sample, label, and embedding counts.")

        return labels, embeddings, sample_names

    def _parse_r_output(self, result: subprocess.CompletedProcess[str]) -> dict:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        payload: dict = {}
        if stdout:
            for line in reversed(stdout.splitlines()):
                candidate = line.strip()
                if not candidate.startswith("{"):
                    continue
                try:
                    payload = json.loads(candidate)
                    break
                except json.JSONDecodeError:
                    continue

        if result.returncode != 0:
            message = payload.get("error") or stderr or stdout or "PIntMF R script failed."
            raise RuntimeError(message)

        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))

        return payload
