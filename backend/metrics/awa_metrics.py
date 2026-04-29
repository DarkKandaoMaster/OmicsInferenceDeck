"""Post-process calculated metrics into AWA and 3D-AWA scores."""

import math
from typing import Any


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _clip_0_10(value: float) -> float:
    return max(0.0, min(10.0, value))


def _bounded_score(value: Any, lower: float, upper: float, higher_is_better: bool = True) -> float:
    number = _number(value)
    if number is None or upper <= lower:
        return 0.0
    ratio = (number - lower) / (upper - lower)
    if not higher_is_better:
        ratio = 1.0 - ratio
    return round(_clip_0_10(ratio * 10.0), 4)


def _positive_unbounded_score(value: Any) -> float:
    number = _number(value)
    if number is None or number <= 0:
        return 0.0
    return round(_clip_0_10(10.0 * number / (number + 1.0)), 4)


def _p_value_score(value: Any) -> float:
    number = _number(value)
    if number is None or number <= 0:
        return 0.0
    return round(_clip_0_10(-math.log10(number)), 4)


def _ratio_score(numerator: Any, denominator: Any) -> float:
    count = _number(numerator)
    total = _number(denominator)
    if count is None or count <= 0:
        return 0.0
    if total is not None and total > 0:
        return round(_clip_0_10(10.0 * count / total), 4)
    return _positive_unbounded_score(count)


def _weighted_mean(values: list[tuple[float, float]]) -> float:
    denominator = sum(weight for _, weight in values)
    if denominator <= 0:
        return 0.0
    score = sum(value * weight for value, weight in values) / denominator
    return round(_clip_0_10(score), 4)


def compute_awa_metrics(
    cluster_metrics: dict[str, Any] | None,
    clinical_metrics: dict[str, Any] | None,
    biology_metrics: dict[str, Any] | None,
    awa_w1: float = 1.0,
    awa_w2: float = 1.0,
) -> dict[str, Any]:
    """Return normalized component scores plus AWA and 3D-AWA.

    All component scores are positive-oriented and mapped to 0..10 before
    aggregation. Missing inputs contribute 0, making incomplete upstream
    analyses visible without failing the whole summary.
    """

    cluster_metrics = cluster_metrics or {}
    clinical_metrics = clinical_metrics or {}
    biology_metrics = biology_metrics or {}

    lrt = clinical_metrics.get("lrt") or {}
    ecp = clinical_metrics.get("ecp") or {}

    components = {
        "silhouette": _bounded_score(cluster_metrics.get("silhouette"), -1.0, 1.0),
        "calinski_harabasz": _positive_unbounded_score(cluster_metrics.get("calinski")),
        "dunn": _positive_unbounded_score(cluster_metrics.get("dunn")),
        "log_rank_test": _p_value_score(lrt.get("p_value")),
        "enriched_clinical_parameters": _ratio_score(
            ecp.get("significant_count"),
            ecp.get("total_parameters"),
        ),
        "significant_pathways": _ratio_score(
            biology_metrics.get("significant_pathway_count"),
            biology_metrics.get("total_pathways"),
        ),
        "core_pathway_score": round(
            _clip_0_10(_number(biology_metrics.get("core_pathway_score")) or 0.0),
            4,
        ),
    }

    awa_w1 = max(_number(awa_w1) or 0.0, 0.0)
    awa_w2 = max(_number(awa_w2) or 0.0, 0.0)
    awa = _weighted_mean(
        [
            (components["silhouette"], awa_w1),
            (components["calinski_harabasz"], awa_w1),
            (components["dunn"], awa_w1),
            (components["log_rank_test"], awa_w2),
            (components["enriched_clinical_parameters"], awa_w2),
        ]
    )

    w3d = 1.0 / 3.0
    three_d_awa = _weighted_mean(
        [
            (components["silhouette"], w3d),
            (components["calinski_harabasz"], w3d),
            (components["dunn"], w3d),
            (components["log_rank_test"], w3d),
            (components["enriched_clinical_parameters"], w3d),
            (components["significant_pathways"], w3d),
            (components["core_pathway_score"], w3d),
        ]
    )

    return {
        "awa": awa,
        "three_d_awa": three_d_awa,
        "scale": "0-10",
        "weights": {
            "awa": {"w1": awa_w1, "w2": awa_w2},
            "three_d_awa": {"w1": w3d, "w2": w3d, "w3": w3d},
        },
        "components": components,
    }
