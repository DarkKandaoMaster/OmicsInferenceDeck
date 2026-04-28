from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plots.base import CLUSTER_RESULT_FILE, empty_svg, plot_path
from plots.cluster_scatter import render_svg as render_cluster_scatter_svg


router = APIRouter()


class ClusterScatterRequest(BaseModel):
    session_id: str
    reduction: str = "PCA"
    random_state: int = 42


def _seed_or_none(random_state: int) -> int | None:
    return None if random_state == -1 else random_state


@router.post("/api/plots/cluster_scatter")
async def cluster_scatter(request: ClusterScatterRequest):
    try:
        path = plot_path(request.session_id, CLUSTER_RESULT_FILE)
        if not path.exists():
            raise FileNotFoundError("cluster_result.parquet not found. Please run clustering first.")

        svg = render_cluster_scatter_svg(str(path), request.reduction, _seed_or_none(request.random_state))
        return {"status": "success", "svg": svg, "reduction": request.reduction}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "success",
            "svg": empty_svg(f"Cluster plot failed: {e}", "Cluster Scatter"),
            "reduction": request.reduction,
        }
