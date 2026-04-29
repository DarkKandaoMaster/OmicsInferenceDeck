import json
import subprocess
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from .base import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    def fit_predict(self, data: dict[str, pd.DataFrame]) -> tuple[np.ndarray, np.ndarray, list[str]]:
        omics_path = self.params.get("omics_path")
        if not omics_path:
            raise ValueError("MOSD requires omics_path so R can read the saved omics_data.parquet directly.")

        input_path = Path(omics_path)
        if not input_path.exists():
            raise FileNotFoundError(f"MOSD input file not found: {input_path}")

        script_path = Path(__file__).with_suffix(".R")
        if not script_path.exists():
            raise FileNotFoundError(f"MOSD R script not found: {script_path}")

        output_path = input_path.with_name(f"mosd_result_{uuid.uuid4().hex}.parquet")
        n_clusters = int(self.params.get("n_clusters", 3))
        random_state = self.params.get("random_state")
        seed_arg = "" if random_state is None else str(int(random_state))

        try:
            result = subprocess.run(
                [
                    "Rscript",
                    str(script_path),
                    str(input_path),
                    str(output_path),
                    str(n_clusters),
                    seed_arg,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=int(self.params.get("timeout", 3600)),
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Rscript not found. Please install R and make sure Rscript is on PATH.") from exc

        payload = self._parse_r_output(result)
        if not output_path.exists():
            raise RuntimeError(payload.get("error") or "MOSD R script did not create an output parquet file.")

        try:
            result_df = pd.read_parquet(output_path)
        finally:
            try:
                output_path.unlink(missing_ok=True)
            except Exception:
                pass

        if "sample_name" not in result_df.columns or "label" not in result_df.columns:
            raise ValueError("MOSD output must contain sample_name and label columns.")

        emb_cols = [col for col in result_df.columns if str(col).startswith("emb_")]
        if not emb_cols:
            raise ValueError("MOSD output must contain at least one emb_ column.")

        labels = result_df["label"].to_numpy(dtype=int)
        embeddings = result_df[emb_cols].to_numpy(dtype=float)
        sample_names = result_df["sample_name"].astype(str).tolist()

        return labels, embeddings, sample_names

    @staticmethod
    def _parse_r_output(result: subprocess.CompletedProcess[str]) -> dict:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        payload: dict = {}
        if stdout:
            try:
                payload = json.loads(stdout.splitlines()[-1])
            except json.JSONDecodeError:
                payload = {}

        if result.returncode != 0:
            message = payload.get("error") or stderr or stdout or "MOSD R script failed."
            raise RuntimeError(message)

        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))

        return payload
