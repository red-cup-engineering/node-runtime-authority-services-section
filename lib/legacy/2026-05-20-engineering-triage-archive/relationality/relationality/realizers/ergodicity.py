from __future__ import annotations

from fractions import Fraction
from typing import Dict, List

from relationality.canonical import ensure_id_coherence, fraction_to_canonical_string
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    ergodicity realizer.

    Inputs
    ------
    fixed_kernel:
        FixedKernel carrier with basis, kernel_matrix, and stationary
        distribution.
    mixing_evidence:
        MixingEvidence carrier witnessing entropy-increasing mixing for the
        same kernel/profile.
    trace:
        Trace carrier whose elements follow the kernel basis.

    Semantics
    ---------
    Realize the Ergodicity act `(FixedKernel Mixing)` by comparing exact
    time averages along the trace with the space average from the stationary
    kernel. The realizer depends on the mixing evidence:

    - requires mixing_evidence.status == \"pass\",
    - requires its independence_witness basis and stationary distribution to
      match those of the fixed kernel,
    - computes time averages as Fractions, compares to the stationary
      distribution exactly, and emits ergodicity_evidence with status and
      first counterexample (if any).
    """
    fixed_kernel = inputs.get("fixed_kernel")
    mixing_evidence = inputs.get("mixing_evidence")
    trace = inputs.get("trace")
    if fixed_kernel is None or mixing_evidence is None or trace is None:
        raise KeyError("ergodicity requires fixed_kernel, mixing_evidence, and trace inputs")
    if fixed_kernel.get("kind") != "fixed_kernel":
        raise LawValidationError("fixed_kernel input must have kind 'fixed_kernel'")
    if mixing_evidence.get("kind") != "mixing_evidence":
        raise LawValidationError("mixing_evidence input must have kind 'mixing_evidence'")
    if trace.get("kind") != "trace":
        raise LawValidationError("trace input must have kind 'trace'")

    if mixing_evidence.get("status") != "pass":
        raise LawValidationError("ergodicity requires mixing_evidence with status 'pass'")

    basis: List[str] = list(fixed_kernel.get("basis", []))
    n = len(basis)
    if n == 0:
        raise LawValidationError("fixed_kernel basis must be non-empty")

    stationarity = fixed_kernel.get("stationarity_evidence") or {}
    space_average_raw = stationarity.get("space_average")
    if not isinstance(space_average_raw, list) or len(space_average_raw) != n:
        raise LawValidationError(
            "fixed_kernel.stationarity_evidence.space_average must exist and match basis length"
        )

    # Ensure mixing evidence was computed for the same kernel/basis by checking
    # its independence witness.
    independence_witness = mixing_evidence.get("independence_witness") or {}
    witness_basis = independence_witness.get("basis")
    witness_stationary = independence_witness.get("stationary_distribution")
    if witness_basis is None or witness_stationary is None:
        raise LawValidationError(
            "ergodicity requires mixing_evidence.independence_witness to record basis and stationary_distribution"
        )
    if witness_basis != basis:
        raise LawValidationError("ergodicity requires mixing_evidence basis to match fixed_kernel basis")
    if witness_stationary != space_average_raw:
        raise LawValidationError(
            "ergodicity requires mixing_evidence stationary_distribution to match fixed_kernel space_average"
        )

    elements: List[str] = list(trace.get("elements", []))
    if not elements:
        raise LawValidationError("trace must contain at least one element to compute time averages")
    basis_index = {name: idx for idx, name in enumerate(basis)}
    counts = [0] * n
    for elt in elements:
        if elt not in basis_index:
            raise LawValidationError(f"trace element {elt} not in fixed_kernel basis")
        counts[basis_index[elt]] += 1
    length = len(elements)
    if length == 0:
        raise LawValidationError("trace must contain at least one element to compute time averages")

    # Exact rational time averages.
    time_average_frac = [Fraction(count, length) for count in counts]
    space_average_frac = [Fraction(str(value)) for value in space_average_raw]

    if len(time_average_frac) != len(space_average_frac):
        raise LawValidationError("time_average and space_average must have the same dimension")

    status = "pass"
    counterexample = None
    for idx, (t_val, s_val) in enumerate(zip(time_average_frac, space_average_frac)):
        if t_val != s_val:
            status = "fail"
            counterexample = {
                "index": idx,
                "time_value": fraction_to_canonical_string(t_val),
                "space_value": fraction_to_canonical_string(space_average_frac[idx]),
            }
            break

    evidence = {
        "kind": "ergodicity_evidence",
        "trace_id": trace["id"],
        "fixed_kernel_id": fixed_kernel["id"],
        "mixing_evidence_id": mixing_evidence["id"],
        "time_average": [fraction_to_canonical_string(value) for value in time_average_frac],
        "space_average": [fraction_to_canonical_string(value) for value in space_average_frac],
        "status": status,
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = []
    for src in (fixed_kernel["id"], mixing_evidence["id"], trace["id"]):
        edges.append(
            {
                "operator": "ergodicity",
                "src": src,
                "tgt": evidence["id"],
            }
        )

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"ergodicity_evidence": evidence["id"]},
    )
