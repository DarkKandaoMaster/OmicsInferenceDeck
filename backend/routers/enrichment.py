from pathlib import Path

import gseapy as gp
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


def _gmt_files(database: str) -> dict[str, str]:
    base = Path("references") / "GO_KEGG"
    if database.upper() == "GO":
        return {
            "BP": str(base / "GO_Biological_Process_2025.gmt"),
            "CC": str(base / "GO_Cellular_Component_2025.gmt"),
            "MF": str(base / "GO_Molecular_Function_2025.gmt"),
        }
    if database.upper() == "KEGG":
        return {"KEGG": str(base / "KEGG_2026.gmt")}
    raise ValueError("database must be GO or KEGG")


def _cluster_genes_from_differential(session_id: str) -> dict[str, list[str]]:
    volcano_path = plot_path(session_id, DIFFERENTIAL_VOLCANO_FILE)
    if not volcano_path.exists():
        raise FileNotFoundError("differential_volcano.parquet not found. Please run differential analysis first.")
    volcano_df = pd.read_parquet(volcano_path)
    cluster_genes: dict[str, list[str]] = {}
    for cluster_id, group in volcano_df.groupby("cluster"):
        significant = group[(group["t_pvalue"] < 0.05) & (group["logFC"] > 0.5)]
        significant = significant.sort_values(["t_pvalue", "logFC"], ascending=[True, False])
        cluster_genes[str(int(cluster_id))] = significant["gene"].astype(str).tolist()
    return cluster_genes


def _rich_factor(overlap: str) -> float:
    try:
        numerator, denominator = str(overlap).split("/")
        return float(numerator) / float(denominator)
    except Exception:
        return 0.0


@router.post("/api/enrichment_analysis")
async def run_enrichment_analysis(request: EnrichmentRequest):
    try:
        database = request.database.upper()
        gmt_files = _gmt_files(database)

        if request.cluster_genes is not None:
            cluster_genes = request.cluster_genes
        else:
            if not request.session_id:
                raise ValueError("session_id is required when cluster_genes is not provided.")
            cluster_genes = _cluster_genes_from_differential(request.session_id)

        rows: list[dict] = []
        for cluster_id, gene_list in cluster_genes.items():
            if len(gene_list) < 3:
                continue

            for category, gmt_file in gmt_files.items():
                enr = gp.enrich(gene_list=gene_list, gene_sets=gmt_file, outdir=None, no_plot=True)
                results_df = enr.results
                if not isinstance(results_df, pd.DataFrame) or results_df.empty:
                    continue

                filtered = results_df[results_df["P-value"] < 0.05].sort_values("P-value")
                top_results = filtered.head(5)
                for _, row in top_results.iterrows():
                    genes = str(row.get("Genes", ""))
                    rows.append(
                        {
                            "cluster": int(cluster_id),
                            "Term": str(row.get("Term", "")),
                            "P_value": float(row.get("P-value", 1.0)),
                            "Adjusted_P": float(row.get("Adjusted P-value", row.get("P-value", 1.0))),
                            "Overlap": str(row.get("Overlap", "")),
                            "Genes": genes,
                            "Gene_Count": len([g for g in genes.split(";") if g]),
                            "Category": category,
                            "Rich_Factor": _rich_factor(str(row.get("Overlap", ""))),
                        }
                    )

        result_df = pd.DataFrame(rows, columns=RESULT_COLUMNS)
        if request.session_id:
            output_path = plot_path(request.session_id, enrichment_file(database))
            result_df.to_parquet(output_path, index=False)
        else:
            output_path = None

        clusters = sorted([int(c) for c in cluster_genes.keys()])
        selected_cluster = clusters[0] if clusters else 0

        if output_path is not None:
            try:
                bar_svg = run_r_svg("enrichment_bar.R", [output_path, selected_cluster])
            except Exception as exc:
                bar_svg = empty_svg(f"Enrichment bar plot failed: {exc}", "Enrichment Bar")
            try:
                bubble_svg = run_r_svg("enrichment_bubble.R", [output_path, "combined"])
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
            "n_terms": int(len(result_df)),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Enrichment analysis failed: {str(e)}")
