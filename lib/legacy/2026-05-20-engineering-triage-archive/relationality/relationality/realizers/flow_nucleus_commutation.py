from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    flow_map = inputs.get("flow_map")
    nucleus_map = inputs.get("nucleus_map")
    if flow_map is None or nucleus_map is None:
        raise KeyError("flow_nucleus_commutation requires flow_map and nucleus_map inputs")
    flow_elements = set(flow_map["elements"])
    nucleus_elements = set(nucleus_map["elements"])
    if flow_elements != nucleus_elements:
        raise LawValidationError("flow_map and nucleus_map must share the same carrier elements")
    carrier_id_flow = flow_map.get("carrier_id")
    carrier_id_nucleus = nucleus_map.get("carrier_id")
    if carrier_id_flow is None and carrier_id_nucleus is None:
        raise LawValidationError("flow_map and nucleus_map must declare a carrier_id")
    if carrier_id_flow is not None and carrier_id_nucleus is not None and carrier_id_flow != carrier_id_nucleus:
        raise LawValidationError("flow_map and nucleus_map must agree on carrier_id")
    carrier_id = carrier_id_flow or carrier_id_nucleus

    flow_table = flow_map["flow_table"]
    nucleus_table = nucleus_map["nucleus_table"]
    table = []
    counterexample = None
    for elt in sorted(flow_elements):
        f_then_nu = nucleus_table[flow_table[elt]]
        nu_then_f = flow_table[nucleus_table[elt]]
        row = {
            "element": elt,
            "flow_then_nucleus": f_then_nu,
            "nucleus_then_flow": nu_then_f,
        }
        table.append(row)
        if counterexample is None and f_then_nu != nu_then_f:
            counterexample = dict(row)
    status = "pass" if counterexample is None else "fail"
    evidence = {
        "kind": "commutation_evidence",
        "carrier_id": carrier_id,
        "flow_id": flow_map["id"],
        "nucleus_id": nucleus_map["id"],
        "table": table,
        "status": status,
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)
    edges = []
    for src in (flow_map["id"], nucleus_map["id"]):
        edges.append(
            {
                "operator": "flow_nucleus_commutation",
                "src": src,
                "tgt": evidence["id"],
            }
        )
    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"commutation_evidence": evidence["id"]},
    )
