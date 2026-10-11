from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    fixed_observe realizer.

    Inputs
    ------
    observation:
        Observation node (kind ``observation``).
    fixed_invariants:
        FixedInvariants node (kind ``fixed_invariants``) describing invariant
        recognitions.

    Semantics
    ---------
    Diagnostic check for FixedObserve: verifies that the observation's
    recognitional element lies in the fixed invariant lattice.

    - status == 'pass' when observation.element ∈ fixed_invariants.elements;
    - status == 'fail' otherwise, with a counterexample.
    """
    observation = inputs.get("observation")
    invariants = inputs.get("fixed_invariants")
    if observation is None or invariants is None:
        raise KeyError("fixed_observe requires 'observation' and 'fixed_invariants' inputs")
    if observation.get("kind") != "observation":
        raise LawValidationError("fixed_observe observation input must have kind 'observation'")
    if invariants.get("kind") != "fixed_invariants":
        raise LawValidationError("fixed_observe fixed_invariants input must have kind 'fixed_invariants'")

    element = observation.get("element")
    if not isinstance(element, str):
        raise LawValidationError("fixed_observe requires observation.element to be a string")
    elements = set(invariants.get("elements", []))

    status = "pass"
    counterexample = None
    if element not in elements:
        status = "fail"
        counterexample = {
            "reason": "observation.element not in fixed_invariants.elements",
            "element": element,
            "fixed_elements": sorted(elements),
        }

    evidence = {
        "kind": "fixed_observe_evidence",
        "observation_id": observation["id"],
        "fixed_invariants_id": invariants["id"],
        "status": status,
        "act_ref": "FixedObserve",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "fixed_observe",
        "src": observation["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"fixed_observe_evidence": evidence["id"]},
    )

