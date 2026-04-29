"""比较不同聚类之间的组学特征差异。

本文件读取 upload.py 保存的组学数据和 run.py 生成的聚类结果，
对每个聚类做“该聚类 vs 其他聚类”的差异分析。它会保存火山图和热图所需的数据，
供 enrichment.py 继续做富集分析，也供 plots.py 重新绘图或下载。
"""

import json
import subprocess
import re
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from routers.upload import EXPRESSION_DATA_FILE, OMICS_DATA_FILE, load_frame_dict

from plots.base import (
    CLUSTER_RESULT_FILE,
    DIFFERENTIAL_HEATMAP_FILE,
    DIFFERENTIAL_META_FILE,
    DIFFERENTIAL_VOLCANO_FILE,
    empty_svg,
    plot_path,
    run_r_svg,
)
from plots.differential_volcano import render_svg as render_volcano_svg


router = APIRouter()
DIFFERENTIAL_SCRIPT = Path(__file__).with_name("differential.R")
DIFFERENTIAL_INPUT_FILE = "differential_input.parquet"
EXPRESSION_MATRIX_SOURCE = "mRNA Expression Matrix"


class DifferentialAnalysisRequest(BaseModel):
    session_id: str
    omics_type: str | None = None
    sample: list[str] | None = None
    labels: list[int] | None = None


def _load_omics_frame(session_id: str, omics_type: str) -> pd.DataFrame:
    omics_path = plot_path(session_id, OMICS_DATA_FILE)
    if not omics_path.exists():
        raise FileNotFoundError("omics_data.parquet not found. Please upload omics data first.")

    data_dict = load_frame_dict(omics_path)
    if omics_type == "All (Concatenated)":
        return pd.concat(list(data_dict.values()), axis=1, join="inner")
    if omics_type not in data_dict:
        raise ValueError(f"Omics type not found: {omics_type}")

    df = data_dict[omics_type].copy()
    suffix = f"_{omics_type}"
    df.columns = [str(col)[: -len(suffix)] if str(col).endswith(suffix) else str(col) for col in df.columns]
    return df


def _load_expression_frame(session_id: str) -> pd.DataFrame | None:
    expression_path = plot_path(session_id, EXPRESSION_DATA_FILE)
    if not expression_path.exists():
        return None

    data_dict = load_frame_dict(expression_path)
    if not data_dict:
        raise ValueError("Uploaded mRNA expression matrix is empty.")
    return next(iter(data_dict.values())).copy()


def _sample_prefix(sample_name: str) -> str:
    parts = re.split(r"[-.]", str(sample_name))
    if len(parts) >= 3:
        return "-".join(parts[:3])
    return str(sample_name)


def _tcga_sample_kind(sample_name: str) -> str | None:
    parts = str(sample_name).split("-")
    if len(parts) < 4:
        return None
    code = parts[3][:2]
    if not code.isdigit():
        return None
    sample_code = int(code)
    if 1 <= sample_code <= 9:
        return "tumor"
    if 10 <= sample_code <= 19:
        return "normal"
    return None


def _collapse_duplicate_gene_columns(df: pd.DataFrame) -> pd.DataFrame:
    if not df.columns.has_duplicates:
        return df
    numeric_df = df.apply(pd.to_numeric, errors="coerce")
    return numeric_df.T.groupby(level=0, sort=False).mean().T


def _rename_reserved_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    reserved = {"sample_name", "Cluster", "SampleType"}
    renamed = df.copy()
    renamed.columns = [f"{column}_feature" if str(column) in reserved else str(column) for column in renamed.columns]
    return renamed


def _load_cluster_info(session_id: str) -> pd.DataFrame:
    cluster_path = plot_path(session_id, CLUSTER_RESULT_FILE)
    if not cluster_path.exists():
        raise FileNotFoundError("cluster_result.parquet not found. Please run clustering first.")
    cluster_df = pd.read_parquet(cluster_path)[["sample_name", "label"]].copy()
    cluster_df["sample_name"] = cluster_df["sample_name"].astype(str)
    cluster_df = cluster_df.rename(columns={"label": "Cluster"}).set_index("sample_name")
    return cluster_df


def _prepare_expression_input(expression_df: pd.DataFrame, cluster_info: pd.DataFrame) -> pd.DataFrame:
    expression_df = expression_df.copy()
    expression_df.index = expression_df.index.astype(str)
    expression_df.columns = [str(column) for column in expression_df.columns]
    expression_df = _collapse_duplicate_gene_columns(expression_df)
    expression_df = _rename_reserved_feature_columns(expression_df)
    expression_df = expression_df.apply(pd.to_numeric, errors="coerce")
    expression_df = expression_df.dropna(axis=1, how="all")
    if expression_df.empty or expression_df.shape[1] < 1:
        raise ValueError("Uploaded mRNA expression matrix contains no analyzable genes.")

    cluster_map_df = cluster_info.reset_index().copy()
    cluster_map_df["prefix"] = cluster_map_df["sample_name"].map(_sample_prefix)
    prefix_to_cluster = (
        cluster_map_df.groupby("prefix")["Cluster"]
        .agg(lambda values: int(pd.Series(values).mode().iloc[0]))
        .to_dict()
    )

    sample_info = pd.DataFrame(index=expression_df.index)
    sample_info["sample_name"] = sample_info.index.astype(str)
    sample_info["prefix"] = sample_info["sample_name"].map(_sample_prefix)
    sample_info["SampleType"] = sample_info["sample_name"].map(_tcga_sample_kind)
    sample_info["Cluster"] = sample_info["prefix"].map(prefix_to_cluster)

    valid = sample_info["Cluster"].notna() & sample_info["SampleType"].isin(["tumor", "normal"])
    if not valid.any():
        raise ValueError(
            "No TCGA tumor/normal expression samples matched the clustering result. "
            "The mRNA expression matrix should use full TCGA sample barcodes such as TCGA-XX-XXXX-01A."
        )

    matched_expression = expression_df.loc[sample_info.index[valid]].copy()
    matched_info = sample_info.loc[valid, ["sample_name", "Cluster", "SampleType"]].copy()
    matched_info["Cluster"] = matched_info["Cluster"].astype(int)
    matched_expression.insert(0, "SampleType", matched_info["SampleType"].values)
    matched_expression.insert(0, "Cluster", matched_info["Cluster"].values)
    matched_expression.insert(0, "sample_name", matched_info["sample_name"].values)
    return matched_expression


def _prepare_cluster_vs_rest_input(omics_df: pd.DataFrame, cluster_info: pd.DataFrame) -> pd.DataFrame:
    omics_df = omics_df.copy()
    omics_df.index = omics_df.index.astype(str)
    omics_df.columns = [str(column) for column in omics_df.columns]
    omics_df = _collapse_duplicate_gene_columns(omics_df)
    omics_df = _rename_reserved_feature_columns(omics_df)
    merged_df = omics_df.join(cluster_info, how="inner")
    if merged_df.empty:
        raise ValueError("No matching samples between omics data and clustering result.")
    merged_df.insert(0, "sample_name", merged_df.index.astype(str))
    return merged_df


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
        raise RuntimeError(f"Invalid R differential output: {stdout[:500]}") from exc

    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload


def _run_differential_r(input_path: Path, volcano_path: Path, heatmap_path: Path) -> dict:
    if not DIFFERENTIAL_SCRIPT.exists():
        raise FileNotFoundError(f"R differential script not found: {DIFFERENTIAL_SCRIPT}")

    result = subprocess.run(
        ["Rscript", str(DIFFERENTIAL_SCRIPT), str(input_path), str(volcano_path), str(heatmap_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
    )
    return _parse_r_payload(result, "R differential script failed")


@router.post("/api/differential_analysis")
async def run_differential_analysis(request: DifferentialAnalysisRequest):
    try:
        cluster_info = _load_cluster_info(request.session_id)
        expression_df = _load_expression_frame(request.session_id)
        use_expression_matrix = expression_df is not None and (
            not request.omics_type or request.omics_type == EXPRESSION_MATRIX_SOURCE
        )

        if use_expression_matrix:
            r_input_df = _prepare_expression_input(expression_df, cluster_info)
            source_type = EXPRESSION_MATRIX_SOURCE
        else:
            if not request.omics_type:
                raise ValueError("omics_type is required when no mRNA expression matrix has been uploaded.")
            df = _load_omics_frame(request.session_id, request.omics_type)
            r_input_df = _prepare_cluster_vs_rest_input(df, cluster_info)
            source_type = request.omics_type

        volcano_path = plot_path(request.session_id, DIFFERENTIAL_VOLCANO_FILE)
        heatmap_path = plot_path(request.session_id, DIFFERENTIAL_HEATMAP_FILE)
        input_path = plot_path(request.session_id, DIFFERENTIAL_INPUT_FILE)
        genes = [column for column in r_input_df.columns if column not in {"sample_name", "Cluster", "SampleType"}]
        r_input_df.to_parquet(input_path, index=False)

        payload = _run_differential_r(input_path, volcano_path, heatmap_path)

        clusters = [int(c) for c in payload.get("clusters", [])]
        selected_cluster = int(payload.get("selected_cluster", clusters[0] if clusters else 0))
        top_genes = [str(gene) for gene in payload.get("top_genes", [])]
        plot_path(request.session_id, DIFFERENTIAL_META_FILE).write_text(
            json.dumps(
                {
                    "omics_type": source_type,
                    "clusters": clusters,
                    "top_genes": top_genes,
                    "mode": payload.get("mode", "cluster_vs_rest"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        try:
            volcano_svg = render_volcano_svg(str(volcano_path), selected_cluster)
        except Exception as exc:
            volcano_svg = empty_svg(f"Volcano plot failed: {exc}", "Differential Volcano")

        try:
            heatmap_svg = run_r_svg("differential_heatmap.R", [heatmap_path])
        except Exception as exc:
            heatmap_svg = empty_svg(f"Heatmap failed: {exc}", "Differential Heatmap")

        return {
            "status": "success",
            "omics_type": source_type,
            "mode": payload.get("mode", "cluster_vs_rest"),
            "clusters": clusters,
            "selected_cluster": selected_cluster,
            "volcano_svg": volcano_svg,
            "heatmap_svg": heatmap_svg,
            "n_features": int(payload.get("n_features", len(genes))),
            "n_top_genes": int(payload.get("n_top_genes", len(top_genes))),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
