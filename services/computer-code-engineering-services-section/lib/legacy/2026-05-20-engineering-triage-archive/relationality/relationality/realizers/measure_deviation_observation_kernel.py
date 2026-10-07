from __future__ import annotations

from fractions import Fraction
from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _to_fraction_matrix(matrix: List[List[object]]) -> List[List[Fraction]]:
    if not isinstance(matrix, list) or not matrix:
        raise LawValidationError(
            "measure_deviation_observation_kernel: kernel_matrix must be a non-empty list of rows"
        )
    frac_matrix: List[List[Fraction]] = []
    row_len: int | None = None
    for row in matrix:
        if not isinstance(row, list) or not row:
            raise LawValidationError(
                "measure_deviation_observation_kernel: each kernel_matrix row must be a non-empty list"
            )
        if row_len is None:
            row_len = len(row)
        elif len(row) != row_len:
            raise LawValidationError(
                "measure_deviation_observation_kernel: kernel_matrix rows must all have the same length"
            )
        frac_matrix.append([Fraction(str(entry)) for entry in row])
    return frac_matrix


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    measure_deviation_observation_kernel realizer.

    Inputs
    ------
    observation_kernel:
        ObservationKernel carrier whose kernel_matrix acts on a finite basis.

    Semantics
    ---------
    Acts: MeasureDeviationObservationKernel = (FixedIdentity ObservationKernel)
    interpreted as L = I − K on the invariant basis.

    This realizer:
    - takes the observation_kernel basis and kernel_matrix K,
    - constructs the deviation operator L = I − K,
    - computes the spectral decomposition of L exactly over the rationals,
    - emits a spectral_geometry carrier with a single operator entry
      \"deviation\".
    """
    kernel = inputs.get("observation_kernel")
    if kernel is None:
        raise KeyError("measure_deviation_observation_kernel requires 'observation_kernel' input")
    if kernel.get("kind") != "observation_kernel":
        raise LawValidationError(
            "measure_deviation_observation_kernel observation_kernel input must have kind 'observation_kernel'"
        )

    basis = list(kernel.get("basis", []))
    if not basis:
        raise LawValidationError("measure_deviation_observation_kernel: basis must be non-empty")
    matrix = kernel.get("kernel_matrix")
    if matrix is None:
        raise LawValidationError("measure_deviation_observation_kernel: kernel_matrix is required")

    K_frac = _to_fraction_matrix(matrix)
    n = len(K_frac)
    if any(len(row) != n for row in K_frac):
        raise LawValidationError(
            "measure_deviation_observation_kernel: kernel_matrix must be square with size equal to basis length"
        )

    # Deviation operator L = I - K.
    L_frac: List[List[Fraction]] = []
    for i in range(n):
        row: List[Fraction] = []
        for j in range(n):
            value = (Fraction(1) if i == j else Fraction(0)) - K_frac[i][j]
            row.append(value)
        L_frac.append(row)

    operator_matrix = [
        [str(entry) for entry in row] for row in L_frac
    ]

    payload = {
        "kind": "deviation_operator",
        "basis": basis,
        "operator_matrix": operator_matrix,
        "kernel_ref": kernel["id"],
        "act_ref": "MeasureDeviationObservationKernel",
    }
    ensure_id_coherence(payload)

    edge = {
        "operator": "measure_deviation_observation_kernel",
        "src": kernel["id"],
        "tgt": payload["id"],
    }

    return RealizerOutput(
        nodes=[payload],
        edges=[edge],
        bindings={"deviation_operator": payload["id"]},
    )
