"""
Local runbook evaluation on top of the ephemeral AOG view.

This module exposes a small, law-respecting entrypoint that:
- loads persisted carriers and runbooks,
- seeds a :class:`LocalGraph` with those carriers,
- executes a chosen runbook against explicitly provided input IDs, and
- returns any newly created carriers alongside the final bindings.

It does **not** rely on the legacy RelationalGraph or global engine; all
execution happens inside a finite LocalGraph view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Tuple

from .canonical import assert_id_coherence, canonicalize_json
from .boot import validate_for_runtime
from .local_graph import LocalGraph, execute_runbook_local
from .validation import LawValidationError


def _build_local_graph_for_runbook(
    objects_by_id: Mapping[str, dict],
    runbook: Mapping[str, object],
    initial_bindings: Mapping[str, str],
) -> LocalGraph:
    """
    Construct a LocalGraph for evaluating ``runbook`` with the given bindings.

    The graph is seeded from:
    - the carriers named in ``initial_bindings``, and
    - a minimal neighbourhood of carriers required by core Acts, such as
      flow carriers for flow maps and term/judgment carriers referenced
      in measurement_frame constraints.
    """
    graph = LocalGraph()

    # Seed graph with explicitly bound inputs.
    declared_inputs = runbook.get("inputs", []) or []
    for spec in declared_inputs:
        role = spec["role"]
        expected_kind = spec["kind"]
        node_id = initial_bindings.get(role)
        if node_id is None:
            raise KeyError(f"missing binding for input role {role!r} for runbook {runbook.get('name')!r}")
        payload = objects_by_id.get(node_id)
        if payload is None:
            raise KeyError(f"binding for role {role!r} references unknown object id {node_id}")
        if payload.get("kind") != expected_kind:
            raise LawValidationError(
                f"binding for role {role!r} has kind {payload.get('kind')} but expected {expected_kind}"
            )
        graph.nodes[node_id] = dict(payload)

    # Minimal neighbourhood expansion based on carrier kind and Acts.
    # This is intentionally conservative and can be extended as needed.
    changed = True
    while changed:
        changed = False
        for node_id, payload in list(graph.nodes.items()):
            kind = payload.get("kind")
            # FlowMap and NucleusMap require their lattice carrier.
            if kind in {"flow_map", "nucleus_map"}:
                carrier_id = payload.get("carrier_id")
                if isinstance(carrier_id, str) and carrier_id not in graph.nodes:
                    carrier = objects_by_id.get(carrier_id)
                    if carrier is not None:
                        graph.nodes[carrier_id] = dict(carrier)
                        changed = True
            # Presheaf requires its site carrier for SheafCondition.
            if kind == "presheaf":
                site_id = payload.get("site_id")
                if isinstance(site_id, str) and site_id not in graph.nodes:
                    site = objects_by_id.get(site_id)
                    if site is not None:
                        graph.nodes[site_id] = dict(site)
                        changed = True
            # MeasurementFrame may reference term/judgment carriers via constraints.
            if kind == "measurement_frame":
                constraints = payload.get("constraints") or {}
                term_id = constraints.get("term_id")
                if isinstance(term_id, str) and term_id not in graph.nodes:
                    term = objects_by_id.get(term_id)
                    if term is not None:
                        graph.nodes[term_id] = dict(term)
                        changed = True
                judgment_id = constraints.get("judgment_id")
                if isinstance(judgment_id, str) and judgment_id not in graph.nodes:
                    judgment = objects_by_id.get(judgment_id)
                    if judgment is not None:
                        graph.nodes[judgment_id] = dict(judgment)
                        changed = True

    return graph


def evaluate_runbook_by_id(
    runbook_id: str,
    initial_bindings: Mapping[str, str],
    *,
    persist: bool = False,
) -> Tuple[Dict[str, dict], Dict[str, str]]:
    """
    Evaluate a persisted runbook against persisted carriers in a local view.

    Parameters
    ----------
    runbook_id:
        Canonical SHA256 id of the runbook to execute (as in data/runbooks).
    initial_bindings:
        Mapping from runbook input roles to carrier ids (from data/objects).

    Returns
    -------
    new_objects, bindings:
        ``new_objects`` is a mapping id -> payload for carriers that did not
        exist in the persisted object index but were created during this
        evaluation. ``bindings`` is the final environment returned by the
        runbook (role -> carrier id).

    When ``persist`` is True, newly created carriers are also written to
    ``data/objects/{id}.{kind}.object.json`` using canonical JSON
    serialization. Existing files with the same id/kind must either be
    byte-identical or absent; conflicting payloads are a hard error.

    Raises
    ------
    KeyError, LawValidationError, ValueError
        If the runbook or required objects are missing, or if bindings
        violate the runbook's typing constraints or carrier laws.
    """
    objects_index, runbooks_index = validate_for_runtime()

    runbook = runbooks_index.by_id.get(runbook_id)
    if runbook is None:
        raise KeyError(f"runbook {runbook_id!r} not found in persisted index")

    # Build a finite LocalGraph derived from the runbook structure and
    # the explicitly provided input bindings.
    graph = _build_local_graph_for_runbook(objects_index.by_id, runbook, dict(initial_bindings))

    # Record existing node ids to detect newly created carriers after evaluation.
    existing_ids = set(graph.nodes.keys())

    bindings = execute_runbook_local(
        graph=graph,
        runbook=runbook,
        initial_bindings=dict(initial_bindings),
    )

    created_ids = set(graph.nodes.keys()) - existing_ids
    new_objects: Dict[str, dict] = {obj_id: graph.nodes[obj_id] for obj_id in created_ids}

    if persist and new_objects:
        _persist_new_objects(new_objects)

    return new_objects, bindings


def _persist_new_objects(
    new_objects: Mapping[str, Mapping[str, object]],
    directory: Path | None = None,
) -> None:
    """
    Persist newly created carriers to ``data/objects``.

    Each payload must already satisfy schema/local laws and carry a
    canonical ``id`` matching its content. Filenames are
    ``{id}.{kind}.object.json`` and contents are written in canonical
    JSON form. If a file already exists for a given id/kind, its payload
    must be byte-identical to the new object; otherwise a ValueError is
    raised.
    """
    from .loaders import OBJECTS_DIR

    target_dir = directory or OBJECTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    for obj_id, payload in new_objects.items():
        if not isinstance(payload, dict):
            raise ValueError(f"cannot persist non-dict payload for {obj_id!r}")
        assert_id_coherence(payload)
        kind = payload.get("kind")
        if not isinstance(kind, str):
            raise ValueError(f"new object {obj_id!r} is missing string 'kind'")
        path = target_dir / f"{obj_id}.{kind}.object.json"
        text = canonicalize_json(payload)
        if path.exists():
            existing = path.read_text()
            if existing != text:
                raise ValueError(
                    f"object file {path} already exists with different payload"
                )
        else:
            path.write_text(text)


__all__ = ["evaluate_runbook_by_id"]
