from __future__ import annotations

from typing import Any, Dict

from relationality.models import RealizerContext, RecognitionObject
from .utils import clone_payload


def realize_transition_law(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    phase_space = clone_payload(input_obj).get("phase_space", {})
    transitioned = phase_space.copy()
    regime = context.diagnostics.get("regime", {})
    constraints = {}
    if isinstance(regime, dict):
        constraints = regime.get("context", {}).get("constraints", {})
        allowed_ops = regime.get("context", {}).get("allowed_operators", [])
        transitioned["allowed_operators"] = allowed_ops
    transitioned["transition_law"] = {
        "stable": True,
        "invariants": phase_space.get("invariants", []),
        "constraints": constraints,
    }
    context.diagnostics.setdefault("spectral_effects", {})["transition_law"] = {
        "constraints": constraints,
        "allowed_operators": transitioned.get("allowed_operators", []),
        "invariants": transitioned["transition_law"]["invariants"],
    }
    return {
        "kind": "PhaseSpace",
        "acts": ["TransitionLaw", "FlowProfile"],
        "payload": {"phase_space": transitioned},
        "metadata": {"source": input_obj.id},
    }
