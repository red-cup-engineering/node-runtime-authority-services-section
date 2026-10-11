from __future__ import annotations

from typing import Any, Dict

from relationality.models import RealizerContext, RecognitionObject
from .utils import clone_payload


def realize_entropy_measure(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    phase_space = clone_payload(input_obj).get("phase_space", {})
    reachable = phase_space.get("reachable", [])
    if reachable:
        import numpy as np

        arr = np.array([abs(float(x)) for x in reachable], dtype=float)
        probs = arr / arr.sum() if arr.sum() else np.ones_like(arr) / len(arr)
        value = float(-(probs * np.log(probs + 1e-12)).sum())
    else:
        value = 0.0
    entropy = {
        "value": value,
        "phase_space_snapshot": phase_space,
    }
    context.diagnostics.setdefault("spectral_effects", {})["entropy_measure"] = {"entropy": value}
    return {
        "kind": "EntropyMeasurement",
        "acts": ["EntropyMeasure", "ProfileEntropy"],
        "payload": {"entropy_measurement": entropy},
        "metadata": {"source": input_obj.id},
    }
