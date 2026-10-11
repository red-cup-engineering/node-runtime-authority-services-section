from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Tuple

from relationality.canonical import ensure_id_coherence, fraction_to_canonical_string
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _to_fraction_matrix(matrix: List[List[object]]) -> List[List[Fraction]]:
    """
    Convert a numeric kernel matrix into Fractions using decimal strings.
    """
    if not isinstance(matrix, list) or not matrix:
        raise LawValidationError("mixing: fixed_kernel.kernel_matrix must be a non-empty list of rows")
    frac_matrix: List[List[Fraction]] = []
    row_length: int | None = None
    for row in matrix:
        if not isinstance(row, list) or not row:
            raise LawValidationError("mixing: each kernel_matrix row must be a non-empty list")
        if row_length is None:
            row_length = len(row)
        elif len(row) != row_length:
            raise LawValidationError("mixing: kernel_matrix rows must all have the same length")
        frac_row = [Fraction(str(entry)) for entry in row]
        frac_matrix.append(frac_row)
    return frac_matrix


def _to_fraction_vector(vector: List[object], expected_len: int) -> List[Fraction]:
    if not isinstance(vector, list) or len(vector) != expected_len:
        raise LawValidationError(
            "mixing: stationary distribution must be a list with length equal to kernel basis"
        )
    return [Fraction(str(entry)) for entry in vector]


def _check_breadth_normalized(matrix: List[List[Fraction]]) -> None:
    """
    Enforce that each outgoing breadth of the kernel (one per invariant basis
    element) sums to exactly 1.
    """
    one = Fraction(1)
    for idx, row in enumerate(matrix):
        if sum(row) != one:
            raise LawValidationError(
                f"mixing: kernel_matrix breadth {idx} must sum to 1 exactly to serve as a normalized transition kernel"
            )


def _multiply_row_vector(vec: List[Fraction], matrix: List[List[Fraction]]) -> List[Fraction]:
    """
    Compute v' = v K where v is a row vector and K is a matrix.
    """
    n_rows = len(matrix)
    if len(vec) != n_rows:
        raise LawValidationError("mixing: distribution vector length must match kernel_matrix dimension")
    n_cols = len(matrix[0])
    result: List[Fraction] = []
    for col in range(n_cols):
        total = sum(vec[row_index] * matrix[row_index][col] for row_index in range(n_rows))
        result.append(total)
    return result


def _total_variation(p: List[Fraction], q: List[Fraction]) -> Fraction:
    """
    Total variation distance between two distributions on the same basis.
    """
    if len(p) != len(q):
        raise LawValidationError("mixing: distributions compared for independence must have the same dimension")
    diff = sum(abs(a - b) for a, b in zip(p, q))
    return diff / 2


def _compute_entropy_path(
    kernel_matrix: List[List[object]],
    stationary: List[object],
    max_steps: int,
) -> Tuple[List[Fraction], List[Fraction]]:
    """
    Compute a finite-time entropy path witnessing mixing.

    We interpret the fixed kernel as a breadth-normalized transition kernel K
    on a finite basis with stationary distribution π. For each time step t, we:

    - evolve delta distributions at each basis element under K,
    - compute the total variation distance between each evolved distribution
      and π,
    - take the worst-case distance δ_t over all starting states,
    - define an entropy-like quantity H_t = 1 - δ_t.

    The resulting path (H_t)_t is monotone non-decreasing exactly when the
    worst-case dependence on the initial state decays over time.
    """
    if max_steps <= 0:
        raise LawValidationError("mixing: max_steps must be a positive integer")
    frac_kernel = _to_fraction_matrix(kernel_matrix)
    n = len(frac_kernel)
    stationary_vec = _to_fraction_vector(stationary, n)
    _check_breadth_normalized(frac_kernel)

    # Initialize one delta distribution per basis element.
    distributions: List[List[Fraction]] = []
    one = Fraction(1)
    zero = Fraction(0)
    for i in range(n):
        vec = [zero] * n
        vec[i] = one
        distributions.append(vec)

    delta_path: List[Fraction] = []

    for step in range(max_steps + 1):
        # Compute worst-case total variation distance at this time step.
        deltas: List[Fraction] = [
            _total_variation(dist, stationary_vec) for dist in distributions
        ]
        delta_t = max(deltas)
        delta_path.append(delta_t)
        # If all starting states have converged to π, further steps are unnecessary.
        if delta_t == zero:
            break
        if step == max_steps:
            break
        # Evolve all distributions one step forward.
        new_distributions = [
            _multiply_row_vector(dist, frac_kernel) for dist in distributions
        ]
        distributions = new_distributions

    entropy_path: List[Fraction] = [one - delta for delta in delta_path]
    return delta_path, entropy_path


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    mixing realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the recognition profile whose mixing
        behaviour we witness.
    fixed_kernel:
        FixedKernel carrier whose kernel_matrix and stationary distribution
        encode the long-time flow on the profile invariants.

    Semantics
    ---------
    Realize the Mixing act `(ProfileMixing Entropy)` by computing a finite-time,
    rational entropy path derived from the fixed kernel:

    - interpret the fixed kernel as a normalized transition kernel on its basis,
    - compute the worst-case total variation distance to the stationary
      distribution from all basis delta states at each step,
    - derive an entropy-like path H_t = 1 - δ_t (Fractions) over a canonical
      finite horizon,
    - emit a mixing_evidence carrier recording this path and an independence
      witness with decay diagnostics.
    """
    profile = inputs.get("profile_topos")
    fixed_kernel = inputs.get("fixed_kernel")
    if profile is None or fixed_kernel is None:
        raise KeyError("mixing requires 'profile_topos' and 'fixed_kernel' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("mixing profile_topos input must have kind 'profile_topos'")
    if fixed_kernel.get("kind") != "fixed_kernel":
        raise LawValidationError("mixing fixed_kernel input must have kind 'fixed_kernel'")

    basis = list(fixed_kernel.get("basis", []))
    matrix = fixed_kernel.get("kernel_matrix")
    stationarity = fixed_kernel.get("stationarity_evidence") or {}
    stationary = stationarity.get("space_average")

    if not basis:
        raise LawValidationError("mixing: fixed_kernel basis must be non-empty")
    if not isinstance(matrix, list):
        raise LawValidationError("mixing: fixed_kernel.kernel_matrix must be a list of rows")
    if stationary is None:
        raise LawValidationError("mixing: fixed_kernel.stationarity_evidence.space_average is required")

    # Ensure the kernel acts on the profile lattice.
    profile_elements = set(profile.get("elements", []))
    if profile_elements and not set(basis).issubset(profile_elements):
        raise LawValidationError(
            "mixing: fixed_kernel basis must be a subset of profile_topos.elements when elements are provided"
        )

    if len(matrix) != len(basis):
        raise LawValidationError(
            "mixing: fixed_kernel.kernel_matrix must have one row per basis element"
        )
    for row in matrix:
        if not isinstance(row, list) or len(row) != len(basis):
            raise LawValidationError(
                "mixing: fixed_kernel.kernel_matrix must be square with size equal to basis length"
            )

    max_steps = max(1, len(basis) * 4)
    delta_path, entropy_path_frac = _compute_entropy_path(matrix, stationary, max_steps)

    # Monotonicity and independence checks in exact rational arithmetic.
    is_monotone = all(
        earlier <= later
        for earlier, later in zip(entropy_path_frac, entropy_path_frac[1:])
    )
    independent = delta_path[-1] == Fraction(0)

    status = "pass" if is_monotone and independent else "fail"

    counterexample = None
    if not is_monotone:
        # First index where entropy decreases.
        for idx in range(1, len(entropy_path_frac)):
            if entropy_path_frac[idx] < entropy_path_frac[idx - 1]:
                counterexample = {
                    "kind": "entropy_monotonicity_violation",
                    "index": idx,
                    "previous": fraction_to_canonical_string(entropy_path_frac[idx - 1]),
                    "current": fraction_to_canonical_string(entropy_path_frac[idx]),
                }
                break
    elif not independent:
        counterexample = {
            "kind": "incomplete_mixing",
            "last_index": len(delta_path) - 1,
            "delta": fraction_to_canonical_string(delta_path[-1]),
            "max_steps": max_steps,
        }

    entropy_path = [fraction_to_canonical_string(value) for value in entropy_path_frac]
    delta_path_numbers = [fraction_to_canonical_string(value) for value in delta_path]

    independence_witness = {
        "basis": basis,
        "stationary_distribution": stationary,
        "delta_path": delta_path_numbers,
        "time_horizon": len(delta_path) - 1,
        "max_steps": max_steps,
    }

    evidence = {
        "kind": "mixing_evidence",
        "profile_id": profile["id"],
        "entropy_path": entropy_path,
        "independence_witness": independence_witness,
        "status": status,
        "act_ref": "Mixing",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample

    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "mixing",
            "src": profile["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "mixing",
            "src": fixed_kernel["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"mixing_evidence": evidence["id"]},
    )
