from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Tuple

from relationality.canonical import ensure_id_coherence, fraction_to_canonical_string
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _iterate_to_fixed_point(matrix: List[List[object]]) -> List[Fraction]:
    """
    Iterate the kernel action exactly until a fixed distribution is reached.

    We interpret ``matrix`` as a breadth-normalized distribution kernel K on a
    finite basis and iterate p_{n+1} = p_n K starting from the uniform
    distribution. Arithmetic is performed exactly using Fraction on the
    decimal representation of inputs. If the iteration does not reach a fixed
    distribution but instead enters a cycle, a LawValidationError is raised.
    """
    n = len(matrix)
    if n == 0:
        raise LawValidationError("fixed_kernel: kernel_matrix must be non-empty")
    K: List[List[Fraction]] = [
        [Fraction(str(entry)) for entry in row] for row in matrix
    ]
    one_over_n = Fraction(1, n)
    current: Tuple[Fraction, ...] = tuple(one_over_n for _ in range(n))
    seen: set[Tuple[Fraction, ...]] = {current}

    def step(vec: Tuple[Fraction, ...]) -> Tuple[Fraction, ...]:
        result: List[Fraction] = []
        for col in range(n):
            value = sum(vec[row_index] * K[row_index][col] for row_index in range(n))
            result.append(value)
        return tuple(result)

    while True:
        nxt = step(current)
        if nxt == current:
            break
        if nxt in seen:
            raise LawValidationError(
                "fixed_kernel: kernel iteration entered a cycle without reaching a fixed point"
            )
        seen.add(nxt)
        current = nxt

    return list(current)


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    fixed_kernel realizer.

    Inputs
    ------
    observation_kernel:
        ObservationKernel carrier with fields `basis` and `kernel_matrix`
        as a finite distribution-valued transition kernel on the fixed
        invariant basis.

    Semantics
    ---------
    Apply the EnsureFixedPoint construction to the observation kernel to
    obtain a stationary kernel:
    - validate matrix shape against the basis;
    - solve for a stationary distribution p exactly over Fractions;
    - emit a fixed_kernel carrier whose kernel_matrix matches the input
      kernel_matrix and whose stationarity_evidence.space_average is p;
    - reference the source observation_kernel via observation_kernel_id.
    """
    obs_kernel = inputs.get("observation_kernel")
    if obs_kernel is None:
        raise KeyError("fixed_kernel requires 'observation_kernel' input")
    if obs_kernel.get("kind") != "observation_kernel":
        raise LawValidationError("fixed_kernel observation_kernel input must have kind 'observation_kernel'")

    basis = list(obs_kernel.get("basis", []))
    matrix = obs_kernel.get("kernel_matrix")
    if not isinstance(matrix, list):
        raise LawValidationError("fixed_kernel observation_kernel.kernel_matrix must be a list of rows")
    if len(basis) == 0:
        raise LawValidationError("fixed_kernel observation_kernel basis must be non-empty")
    if len(matrix) != len(basis):
        raise LawValidationError("fixed_kernel observation_kernel.kernel_matrix must have one row per basis element")
    for row in matrix:
        if not isinstance(row, list) or len(row) != len(basis):
            raise LawValidationError("fixed_kernel observation_kernel.kernel_matrix must be square with size equal to basis length")

    space_average_frac = _iterate_to_fixed_point(matrix)
    space_average = [fraction_to_canonical_string(v) for v in space_average_frac]

    # Kernel matrix entries must be canonical rational strings as well.
    canonical_matrix: List[List[str]] = []
    for row in matrix:
        canonical_row: List[str] = []
        for entry in row:
            frac = Fraction(str(entry))
            canonical_row.append(fraction_to_canonical_string(frac))
        canonical_matrix.append(canonical_row)

    fixed_kernel = {
        "kind": "fixed_kernel",
        "basis": basis,
        "kernel_matrix": canonical_matrix,
        "stationarity_evidence": {
            "space_average": space_average,
            "observation_kernel_id": obs_kernel["id"],
        },
        "act_ref": "FixedKernel",
    }
    ensure_id_coherence(fixed_kernel)

    edge = {
        "operator": "fixed_kernel",
        "src": obs_kernel["id"],
        "tgt": fixed_kernel["id"],
    }

    return RealizerOutput(
        nodes=[fixed_kernel],
        edges=[edge],
        bindings={"fixed_kernel": fixed_kernel["id"]},
    )
