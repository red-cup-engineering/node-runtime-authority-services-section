"""Shared measurement algebra helpers.

These functions implement the numeric parts of the measurement
algebra used by per-act handlers (measure, entropy, profile-measure,
profile-integral).
"""

from __future__ import annotations

from typing import Any, Dict, List


def compute_expectation(observable: Any, distribution: Dict) -> float:
    """Compute expectation E[X] = sum(x * p(x)) over distribution."""
    import math

    if isinstance(observable, (int, float)):
        return float(observable)

    if isinstance(observable, list):
        if not observable:
            return 0.0

        probs = distribution.get("probabilities", [])
        if probs and len(probs) == len(observable):
            total_prob = sum(probs) or 1.0
            return sum(
                v * (p / total_prob)
                for v, p in zip(observable, probs)
                if isinstance(v, (int, float))
            )

        return sum(v for v in observable if isinstance(v, (int, float))) / len(
            observable
        )

    if isinstance(observable, dict):
        values = observable.get("values", [])
        probs = observable.get(
            "probabilities", distribution.get("probabilities", [])
        )

        if values and probs and len(values) == len(probs):
            total_prob = sum(probs) or 1.0
            return sum(
                v * (p / total_prob)
                for v, p in zip(values, probs)
                if isinstance(v, (int, float))
            )

        if values:
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            return (
                sum(numeric_values) / len(numeric_values) if numeric_values else 0.0
            )

    return 0.0


def compute_entropy(distribution: Dict, entropy_type: str = "shannon") -> float:
    """Compute entropy H(X) = -sum(p(x) * log(p(x))) over distribution."""
    import math

    probs = distribution.get("probabilities", [])

    if not probs:
        values = distribution.get("values", [])
        if values:
            n = len(values)
            probs = [1.0 / n] * n

    if not probs:
        return 0.0

    total_prob = sum(
        p for p in probs if isinstance(p, (int, float)) and p > 0
    )
    if total_prob <= 0:
        return 0.0

    normalized_probs = [
        p / total_prob for p in probs if isinstance(p, (int, float)) and p > 0
    ]

    entropy = 0.0
    for p in normalized_probs:
        if p > 0:
            if entropy_type == "binary":
                entropy -= p * math.log2(p)
            else:
                entropy -= p * math.log(p)

    return entropy


def _compute_depth(obj: Any, current_depth: int = 0) -> int:
    """Compute the nesting depth of a structure."""
    if isinstance(obj, dict):
        if not obj:
            return current_depth + 1
        return max(_compute_depth(v, current_depth + 1) for v in obj.values())
    elif isinstance(obj, (list, tuple)):
        if not obj:
            return current_depth + 1
        return max(_compute_depth(v, current_depth + 1) for v in obj)
    else:
        return current_depth


def measure_observable(target: Any, observable_type: str) -> float:
    """Measure an observable from the target based on observable_type."""
    if target is None:
        return 0.0

    if observable_type == "count":
        if isinstance(target, (list, tuple)):
            return float(len(target))
        elif isinstance(target, dict):
            return float(len(target))
        elif isinstance(target, (int, float)):
            return 1.0
        elif isinstance(target, str):
            return 1.0
        else:
            return 1.0

    elif observable_type == "size":
        if isinstance(target, str):
            return float(len(target.encode("utf-8")))
        elif isinstance(target, (list, tuple)):
            return float(len(target))
        elif isinstance(target, dict):
            return float(len(target))
        else:
            return 1.0

    elif observable_type == "value":
        if isinstance(target, (int, float)):
            return float(target)
        elif isinstance(target, dict) and "value" in target:
            val = target["value"]
            if isinstance(val, (int, float)):
                return float(val)
        return 0.0

    elif observable_type == "length":
        if isinstance(target, (str, list, tuple)):
            return float(len(target))
        elif isinstance(target, dict):
            return float(len(target))
        return 0.0

    elif observable_type == "depth":
        return float(_compute_depth(target))

    else:
        if isinstance(target, (int, float)):
            return float(target)
        return 1.0


def aggregate_measurements(measurements: List[Dict], aggregation_type: str) -> float:
    """Aggregate measurement values using the specified aggregation type."""
    total_measurement_count = len(measurements)

    numeric_values: List[float] = []
    for m in measurements:
        if isinstance(m, dict):
            val = m.get("value")
            if val is not None and isinstance(val, (int, float)):
                numeric_values.append(float(val))

    if aggregation_type == "count":
        return float(total_measurement_count)

    if not numeric_values:
        return 0.0

    if aggregation_type == "sum":
        return sum(numeric_values)
    elif aggregation_type == "mean":
        return sum(numeric_values) / len(numeric_values)
    elif aggregation_type == "min":
        return min(numeric_values)
    elif aggregation_type == "max":
        return max(numeric_values)
    elif aggregation_type == "product":
        result = 1.0
        for v in numeric_values:
            result *= v
        return result
    else:
        return sum(numeric_values)

