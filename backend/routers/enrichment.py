"""对差异分析得到的基因做 GO 或 KEGG 富集分析。

本文件通常读取 differential.py 保存的 differential_volcano.parquet，从每个聚类中
挑出显著基因，再用本地 GO/KEGG 参考文件做富集分析。结果会保存为 enrichment
文件，并返回前端可显示的柱状图和气泡图 SVG。
"""

from pathlib import Path
import json
import subprocess
import tempfile

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plots.base import (
    DIFFERENTIAL_VOLCANO_FILE,
    empty_svg,
    enrichment_file,
    plot_path,
    run_r_svg,
)


router = APIRouter()
ENRICHMENT_SCRIPT = Path(__file__).with_name("enrichment.R")
ENRICHMENT_CLUSTER_GENES_FILE = "enrichment_cluster_genes.parquet"


class EnrichmentRequest(BaseModel):
    database: str
    session_id: str | None = None
    cluster_genes: dict[str, list[str]] | None = None


RESULT_COLUMNS = [
    "cluster",
    "Term",
    "P_value",
    "Adjusted_P",
    "Overlap",
    "Genes",
    "Gene_Count",
    "Category",
    "Rich_Factor",
]


def _parse_r_payload(result: subprocess.CompletedProcess[str], fallback_message: str) -> dict:
    stdout = result.stdout.strip()
    if result.returncode != 0:
        message = stdout or result.stderr.strip() or fallback_message
        try:
            message = json.loads(stdout).get("error", message)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(message)

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid R enrichment output: {stdout[:500]}") from exc

    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload


def _run_enrichment_r(database: str, input_path: Path, output_path: Path, input_mode: str) -> dict:
    if not ENRICHMENT_SCRIPT.exists():
        raise FileNotFoundError(f"R enrichment script not found: {ENRICHMENT_SCRIPT}")

    gmt_base = Path(__file__).resolve().parents[1] / "references" / "GO_KEGG"
    result = subprocess.run(
        [
            "Rscript",
            str(ENRICHMENT_SCRIPT),
            database,
            str(input_path),
            str(output_path),
            str(gmt_base),
            input_mode,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
    )
    return _parse_r_payload(result, "R enrichment script failed")


def _write_cluster_genes_input(cluster_genes: dict[str, list[str]], output_path: Path) -> None:
    rows: list[dict] = []
    for cluster_id, genes in cluster_genes.items():
        for gene in genes:
            rows.append({"cluster": int(cluster_id), "gene": str(gene)})
    pd.DataFrame(rows, columns=["cluster", "gene"]).to_parquet(output_path, index=False)


@router.post("/api/enrichment_analysis")
async def run_enrichment_analysis(request: EnrichmentRequest):
    try:
        database = request.database.upper()
        if database not in {"GO", "KEGG"}:
            raise ValueError("database must be GO or KEGG")

        if request.session_id:
            output_path = plot_path(request.session_id, enrichment_file(database))
        else:
            output_path = None

        temp_dir_context = tempfile.TemporaryDirectory() if output_path is None else None
        try:
            if output_path is None:
                output_path = Path(temp_dir_context.name) / enrichment_file(database)

            if request.cluster_genes is not None:
                if request.session_id:
                    input_path = plot_path(request.session_id, ENRICHMENT_CLUSTER_GENES_FILE)
                else:
                    input_path = Path(temp_dir_context.name) / ENRICHMENT_CLUSTER_GENES_FILE
                _write_cluster_genes_input(request.cluster_genes, input_path)
                input_mode = "genes"
            else:
                if not request.session_id:
                    raise ValueError("session_id is required when cluster_genes is not provided.")
                input_path = plot_path(request.session_id, DIFFERENTIAL_VOLCANO_FILE)
                if not input_path.exists():
                    raise FileNotFoundError("differential_volcano.parquet not found. Please run differential analysis first.")
                input_mode = "volcano"

            payload = _run_enrichment_r(database, input_path, output_path, input_mode)
        finally:
            if temp_dir_context is not None:
                temp_dir_context.cleanup()

        clusters = [int(c) for c in payload.get("clusters", [])]
        selected_cluster = int(payload.get("selected_cluster", clusters[0] if clusters else 0))

        if request.session_id:
            render_path = plot_path(request.session_id, enrichment_file(database))
            try:
                bar_svg = run_r_svg("enrichment_bar.R", [render_path, selected_cluster])
            except Exception as exc:
                bar_svg = empty_svg(f"Enrichment bar plot failed: {exc}", "Enrichment Bar")
            try:
                bubble_svg = run_r_svg("enrichment_bubble.R", [render_path, "combined"])
            except Exception as exc:
                bubble_svg = empty_svg(f"Enrichment bubble plot failed: {exc}", "Enrichment Bubble")
        else:
            bar_svg = empty_svg("Run session-based enrichment to render SVG.", "Enrichment Bar")
            bubble_svg = empty_svg("Run session-based enrichment to render SVG.", "Enrichment Bubble")

        return {
            "status": "success",
            "database": database,
            "clusters": clusters,
            "selected_cluster": selected_cluster,
            "bar_svg": bar_svg,
            "bubble_svg": bubble_svg,
            "n_terms": int(payload.get("n_terms", 0)),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Enrichment analysis failed: {str(e)}")
