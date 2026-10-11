from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_object


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    measure_preservation realizer.

    Input
    -----
    kernel:
        FixedKernel carrier (kind ``fixed_kernel``) whose stationarity
        evidence witnesses an invariant measure.

    Semantics
    ---------
    For kernels, measure-preservation is witnessed exactly by the
    stationarity condition already enforced on fixed_kernel carriers:
    the space_average is an invariant vector for the kernel_matrix.

    This realizer therefore:
    - validates the fixed_kernel payload;
    - emits a measure_preservation_evidence node with status \"preserving\"
      and witnesses echoing the stationarity_evidence.

    Flow-map based measure preservation is reserved for future acts once
    explicit measure carriers are present; in this implementation,
    measure_preservation is defined only for fixed kernels.
    """
    kernel = inputs.get("kernel")
    if kernel is None:
        raise KeyError("measure_preservation requires 'kernel' input")
    if kernel.get("kind") != "fixed_kernel":
        raise LawValidationError("measure_preservation kernel input must have kind 'fixed_kernel'")

    # Ensure the kernel satisfies the fixed_kernel laws (including exact
    # stationarity) before using it as a measure-preserving witness.
    validate_object(kernel)

    stationarity = kernel.get("stationarity_evidence", {})
    witnesses = {
        "basis": kernel.get("basis", []),
        "space_average": stationarity.get("space_average"),
        "observation_kernel_id": stationarity.get("observation_kernel_id"),
    }
    evidence = {
        "kind": "measure_preservation_evidence",
        "operator_ref": kernel["id"],
        "status": "preserving",
        "witnesses": witnesses,
        "act_ref": "MeasurePreservation",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "measure_preservation",
        "src": kernel["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"measure_preservation_evidence": evidence["id"]},
    )

