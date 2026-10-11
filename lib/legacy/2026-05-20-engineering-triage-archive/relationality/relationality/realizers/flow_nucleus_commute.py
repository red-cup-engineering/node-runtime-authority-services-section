from __future__ import annotations

from typing import Any, Dict

import orjson

from relationality.models import RealizerContext, RecognitionObject
from .utils import clone_payload


def realize_flow_nucleus_commute(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    """Compute Flow→Nucleus and Nucleus→Flow commutation evidence."""
    stabilized = clone_payload(input_obj).get("stabilized_observation", {})
    normalized = stabilized.get("normalized_observation", {})

    flow_first = {"flow": normalized}
    nucleus_first = {"nucleus": normalized}
    evidence = {
        "flow_first": flow_first,
        "nucleus_first": nucleus_first,
    }
    commutes = flow_first == nucleus_first
    evidence["commutes"] = commutes
    if not commutes:
        context.diagnostics.setdefault("violations", []).append("flow_nucleus_commutation")

    context.diagnostics.setdefault("commutation_evidence", {})["flow_nucleus_commute"] = evidence
    signature = orjson.dumps(evidence, option=orjson.OPT_SORT_KEYS).decode()
    return {
        "kind": "FixedInvariant",
        "acts": ["FixFlowNucleus", "FixedInvariant"],
        "payload": {"fixed_invariant": {"commutation": evidence, "signature": signature}},
        "metadata": {"source": input_obj.id},
    }
