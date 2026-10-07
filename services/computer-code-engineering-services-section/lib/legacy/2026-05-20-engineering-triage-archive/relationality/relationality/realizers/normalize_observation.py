from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.observation_equivalence_utils import (
    canonicalize_observation_element,
    find_observation_equivalence,
    make_trivial_observation_equivalence,
)
from relationality.observation_utils import record_observation
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    normalize_observation realizer.

    Input
    -----
    observation:
        Measured Observation carrier (kind ``observation``).

    Semantics
    ---------
    Realizes the NormalizeObservation act by mapping observation elements to
    canonical representatives of an observation-equivalence relation when
    such a carrier is present in the AOG.

    - When an observation_equivalence carrier exists whose observation_ids
      contain the observation's element, the element is replaced by the
      canonical representative of its equivalence class.
    - When no such carrier is present, a trivial observation_equivalence
      carrier is created for this element and inserted into the AOG, so
      normalization always has an explicit equivalence context.
    """
    measured = inputs.get("observation")
    if measured is None:
        raise KeyError("normalize_observation requires 'observation' input")
    if measured.get("kind") != "observation":
        raise LawValidationError("normalize_observation input must have kind 'observation'")

    element = measured.get("element")
    if not isinstance(element, str):
        raise LawValidationError("normalize_observation requires observation.element to be a string")

    # Locate or create the observation_equivalence carrier governing this
    # element. Creation is per-graph (and thus per-System when operating on a
    # system subgraph).
    eq = find_observation_equivalence(graph, element)
    created_eq: dict | None = None
    if eq is None:
        # Use the observation carrier as a minimal witness for the new
        # equivalence; this ties the equivalence to the same ambient
        # recognitional context.
        witness_id = measured["carrier_id"]
        eq = make_trivial_observation_equivalence(element, witness_id)
        ensure_id_coherence(eq)
        created_eq = eq

    canonical_element, iteration_count = canonicalize_observation_element(eq, element)

    normalized = record_observation(
        carrier_id=measured["carrier_id"],
        measurement_frame_id=measured["measurement_frame_id"],
        element=canonical_element,
        act_ref="NormalizeObservation",
    )

    # Evidence that normalization reached a fixed point under the equivalence.
    evidence = {
        "kind": "normalized_observation_evidence",
        "observation_id": normalized["id"],
        "iteration_count": iteration_count,
        "status": "pass",
        "act_ref": "NormalizeObservation",
    }
    ensure_id_coherence(evidence)

    edge_observation = {
        "operator": "normalize_observation",
        "src": measured["id"],
        "tgt": normalized["id"],
    }
    edge_evidence = {
        "operator": "normalize_observation",
        "src": normalized["id"],
        "tgt": evidence["id"],
    }
    edge_equivalence = {
        "operator": "normalize_observation",
        "src": eq["id"],
        "tgt": evidence["id"],
    }

    nodes: List[dict] = [normalized, evidence]
    if created_eq is not None:
        nodes.insert(0, created_eq)

    return RealizerOutput(
        nodes=nodes,
        edges=[edge_observation, edge_evidence, edge_equivalence],
        bindings={"observation": normalized["id"]},
    )
