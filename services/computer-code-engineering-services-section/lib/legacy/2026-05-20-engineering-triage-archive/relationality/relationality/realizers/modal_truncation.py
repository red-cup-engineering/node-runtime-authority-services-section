from __future__ import annotations

from typing import Dict, List, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace, validate_temporal_modality


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    modal_truncation realizer.

    Inputs
    ------
    trace:
        Trace carrier whose elements lie in the temporal modality basis.
    temporal_modality:
        TemporalModality carrier providing always/eventually tables over a
        fixed invariant basis.

    Semantics
    ---------
    ModalTruncation = (FixedNucleateProfile LoopHIT) collapses higher paths
    by truncating trace elements along the temporal modality. In this finite
    setting, we interpret truncation as pointwise application of the 'always'
    table:

        t_trunc[i] = □(t[i])

    for each element of the trace, yielding a new trace whose elements are
    the always-closed images of the original elements.
    """
    trace = inputs.get("trace")
    modality = inputs.get("temporal_modality")
    if trace is None or modality is None:
        raise KeyError("modal_truncation requires 'trace' and 'temporal_modality' inputs")
    if trace.get("kind") != "trace":
        raise LawValidationError("modal_truncation trace input must have kind 'trace'")
    if modality.get("kind") != "temporal_modality":
        raise LawValidationError("modal_truncation temporal_modality input must have kind 'temporal_modality'")

    validate_trace(trace)
    validate_temporal_modality(modality)

    elements: List[str] = list(trace.get("elements", []))
    if not elements:
        raise LawValidationError("modal_truncation requires a non-empty trace")

    basis: List[str] = list(modality.get("basis", []))
    basis_set = set(basis)
    always_table: Mapping[str, str] = modality.get("always_table") or {}

    if not set(elements).issubset(basis_set):
        raise LawValidationError(
            "modal_truncation requires trace.elements to be contained in temporal_modality.basis"
        )

    new_elements: List[str] = []
    for elt in elements:
        image = always_table.get(elt)
        if image is None:
            raise LawValidationError(
                "temporal_modality.always_table must be total on its basis elements"
            )
        if image not in basis_set:
            raise LawValidationError(
                "temporal_modality.always_table must map within its basis"
            )
        new_elements.append(image)

    new_trace = {
        "kind": "trace",
        "elements": new_elements,
        "head": new_elements[0],
        "tail": new_elements[1:],
    }
    # Preserve shuffle metadata when present; truncation does not change the
    # positional structure, only the recognitional payload.
    shuffle = trace.get("shuffle_metadata")
    if shuffle is not None:
        new_trace["shuffle_metadata"] = shuffle
    ensure_id_coherence(new_trace)

    edges = [
        {
            "operator": "modal_truncation",
            "src": trace["id"],
            "tgt": new_trace["id"],
        },
        {
            "operator": "modal_truncation",
            "src": modality["id"],
            "tgt": new_trace["id"],
        },
    ]

    return RealizerOutput(
        nodes=[new_trace],
        edges=edges,
        bindings={"trace": new_trace["id"]},
    )

