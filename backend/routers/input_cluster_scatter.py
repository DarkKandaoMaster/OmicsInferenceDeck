"""聚类前的输入空间散点图端点。

读取原始组学数据和 cluster_result.parquet，把所有模态横向拼接后降维，
按算法预测的 label 着色，用以对照聚类后的 Cluster Scatter。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plots.base import CLUSTER_RESULT_FILE, empty_svg, plot_path
from plots.input_cluster_scatter import render_svg as render_input_cluster_scatter_svg
from routers.upload import OMICS_DATA_FILE


router = APIRouter()


class InputClusterScatterRequest(BaseModel):
    session_id: str
    reduction: str = "t-SNE"
    random_state: int = 42


def _seed_or_none(random_state: int) -> int | None:
    return None if random_state == -1 else random_state


@router.post("/api/plots/input_cluster_scatter")
async def input_cluster_scatter(request: InputClusterScatterRequest):
    try:
        omics_path = plot_path(request.session_id, OMICS_DATA_FILE)
        cluster_path = plot_path(request.session_id, CLUSTER_RESULT_FILE)
        if not omics_path.exists():
            raise FileNotFoundError("omics_data.parquet not found. Please upload omics data first.")
        if not cluster_path.exists():
            raise FileNotFoundError("cluster_result.parquet not found. Please run clustering first.")

        svg = render_input_cluster_scatter_svg(
            str(omics_path),
            str(cluster_path),
            request.reduction,
            _seed_or_none(request.random_state),
        )
        return {"status": "success", "svg": svg, "reduction": request.reduction}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "success",
            "svg": empty_svg(f"Input cluster plot failed: {e}", "Input Cluster Scatter"),
            "reduction": request.reduction,
        }
