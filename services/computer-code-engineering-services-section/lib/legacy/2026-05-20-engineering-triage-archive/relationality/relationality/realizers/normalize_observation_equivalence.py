from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _canonical_classes(eq: dict) -> List[List[str]]:
    """
    Derive a canonical list of equivalence classes from an observation_equivalence
    carrier, sorting both classes and members for determinism.
    """
    obs_ids = list(eq.get("observation_ids", []))
    obs_set = set(obs_ids)
    classes = eq.get("equivalence_classes")
    relation_table = eq.get("relation_table")
    if classes:
        canonical: List[List[str]] = []
        for cls in classes:
            sorted_cls = sorted(cls)
            canonical.append(sorted_cls)
        canonical.sort(key=lambda c: c[0])
        return canonical
    if relation_table:
        # Build adjacency and extract connected components under the equivalence.
        adj: dict[str, set[str]] = {o: set() for o in obs_ids}
        for a, b in relation_table:
            if a in obs_set and b in obs_set:
                adj[a].add(b)
                adj[b].add(a)
        visited: set[str] = set()
        components: List[List[str]] = []
        for root in sorted(obs_ids):
            if root in visited:
                continue
            stack = [root]
            component: set[str] = set()
            while stack:
                x = stack.pop()
                if x in visited:
                    continue
                visited.add(x)
                component.add(x)
                stack.extend(adj[x] - visited)
            components.append(sorted(component))
        components.sort(key=lambda c: c[0])
        return components
    # Shape should already be rejected by validation; this is a defensive guard.
    raise LawValidationError(
        "normalize_observation_equivalence requires equivalence_classes or relation_table"
    )


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    normalize_observation_equivalence realizer.

    Input
    -----
    observation_equivalence:
        Evaluated ObservationEquivalence carrier.

    Semantics
    ---------
    Compute a canonical partition of observation_ids into equivalence classes
    and emit an observation_equivalence_evidence node whose normalization
    witnesses record this partition alongside an iteration count.
    """
    eq = inputs.get("observation_equivalence")
    if eq is None:
        raise KeyError("normalize_observation_equivalence requires 'observation_equivalence' input")
    if eq.get("kind") != "observation_equivalence":
        raise LawValidationError(
            "normalize_observation_equivalence input must have kind 'observation_equivalence'"
        )

    classes = _canonical_classes(eq)
    obs_ids = eq.get("observation_ids", [])

    # Derive the canonical equivalence_table from the classes and ensure it
    # agrees with the carrier's stored table. This ties the witness
    # normalization directly to the carrier-level normalization map used by
    # NormalizeObservation/StabilizeObservation.
    derived_table: dict[str, str] = {}
    for cls in classes:
        representative = cls[0]
        for element in cls:
            derived_table[element] = representative
    existing_table = eq.get("equivalence_table")
    if not isinstance(existing_table, dict):
        raise LawValidationError(
            "normalize_observation_equivalence requires observation_equivalence with an equivalence_table"
        )
    if derived_table != existing_table:
        raise LawValidationError(
            "normalize_observation_equivalence: derived equivalence_table does not "
            "match observation_equivalence.equivalence_table"
        )

    evidence = {
        "kind": "observation_equivalence_evidence",
        "equivalence_id": eq["id"],
        "evaluation_witnesses": {
            "observation_count": len(obs_ids),
            "class_count": len(classes),
        },
        "normalization_witnesses": {
            "classes": classes,
            "equivalence_table": derived_table,
            "iterations": 1,
        },
        "status": "pass",
        "act_ref": "NormalizeObservationEquivalence",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "normalize_observation_equivalence",
        "src": eq["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"observation_equivalence_evidence": evidence["id"]},
    )
