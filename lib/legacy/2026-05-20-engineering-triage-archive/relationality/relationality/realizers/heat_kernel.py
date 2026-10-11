from __future__ import annotations

from typing import Any, Dict

import numpy as np

from relationality.models import RealizerContext, RecognitionObject
from .utils import clone_payload


def realize_heat_kernel(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    spectral = clone_payload(input_obj).get("spectral_geometry", {})
    eigenvalues = spectral.get("eigenvalues", [0.0])
    damped = [float(np.exp(-abs(v))) for v in eigenvalues]
    invariants = [{"eigenvalue": ev, "decay": dv} for ev, dv in zip(eigenvalues, damped)]
    half_lives = [float(np.log(2) / abs(ev)) if ev else float("inf") for ev in eigenvalues]
    phase_state = {"state": "heat-propagated", "reachable": damped, "invariants": invariants}
    context.diagnostics.setdefault("spectral_effects", {})["heat_kernel"] = {
        "damped": damped,
        "invariants": invariants,
        "half_lives": half_lives,
    }
    return {
        "kind": "PhaseSpace",
        "acts": ["HeatKernel", "FlowProfile"],
        "payload": {"phase_space": phase_state},
        "metadata": {"source": input_obj.id},
    }
