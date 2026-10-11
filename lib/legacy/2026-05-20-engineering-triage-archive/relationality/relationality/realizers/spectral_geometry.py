from __future__ import annotations

from fractions import Fraction
from math import gcd, isqrt
from typing import Dict, List, Tuple

from relationality.canonical import ensure_id_coherence, fraction_to_canonical_string, sorted_unique
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _fraction_flow_matrices(flow_map: dict) -> Tuple[List[str], List[List[Fraction]], List[List[Fraction]]]:
    """
    Build flow and deviation matrices as Fractions from a flow_map carrier.

    The flow operator is encoded as a row-stochastic matrix F where each row
    has a single 1 corresponding to the successor in ``flow_table``. The
    deviation operator is defined as L = I - F on the same basis.
    """
    elements = list(flow_map.get("elements") or [])
    if not elements:
        raise LawValidationError("spectral_geometry: flow_map.elements must be a non-empty list")
    basis = sorted_unique(elements)
    index = {name: idx for idx, name in enumerate(basis)}
    flow_table = flow_map.get("flow_table") or {}
    if set(flow_table.keys()) != set(basis):
        raise LawValidationError(
            "spectral_geometry: flow_map.flow_table must provide an image for every basis element"
        )

    n = len(basis)
    flow_matrix: List[List[Fraction]] = []
    for src in basis:
        row = [Fraction(0) for _ in range(n)]
        tgt = flow_table.get(src)
        if tgt not in index:
            raise LawValidationError(
                f"spectral_geometry: flow_map.flow_table maps {src!r} to unknown element {tgt!r}"
            )
        row[index[tgt]] = Fraction(1)
        flow_matrix.append(row)

    # Deviation operator L = I - F.
    deviation_matrix: List[List[Fraction]] = []
    for i, row in enumerate(flow_matrix):
        dev_row: List[Fraction] = []
        for j, entry in enumerate(row):
            if i == j:
                dev_row.append(Fraction(1) - entry)
            else:
                dev_row.append(-entry)
        deviation_matrix.append(dev_row)

    return basis, flow_matrix, deviation_matrix


def _is_perfect_square_fraction(value: Fraction) -> bool:
    if value < 0:
        return False
    num = value.numerator
    den = value.denominator
    sqrt_num = isqrt(num)
    sqrt_den = isqrt(den)
    return sqrt_num * sqrt_num == num and sqrt_den * sqrt_den == den


def _sqrt_fraction(value: Fraction) -> Fraction:
    if not _is_perfect_square_fraction(value):
        raise LawValidationError(f"spectral_geometry: value {value!r} is not a perfect square rational")
    num = value.numerator
    den = value.denominator
    return Fraction(isqrt(num), isqrt(den))


def _matrix_to_integer(matrix: List[List[Fraction]]) -> Tuple[List[List[int]], int]:
    """
    Scale a rational matrix to an integer matrix.

    Returns (A_int, D) such that matrix = (1/D) * A_int.
    """
    if not matrix or not matrix[0]:
        raise LawValidationError("spectral_geometry: operator matrix must be non-empty and square")
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise LawValidationError("spectral_geometry: operator matrix must be square")
    denom_lcm = 1
    for row in matrix:
        for entry in row:
            d = entry.denominator
            if d != 1:
                denom_lcm = denom_lcm * d // gcd(denom_lcm, d)
    A_int: List[List[int]] = []
    for row in matrix:
        A_int.append([int(entry * denom_lcm) for entry in row])
    return A_int, denom_lcm


def _mat_mul(A: List[List[Fraction]], B: List[List[Fraction]]) -> List[List[Fraction]]:
    n = len(A)
    m = len(B[0])
    res: List[List[Fraction]] = [[Fraction(0) for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for k in range(len(B)):
            aik = A[i][k]
            if aik == 0:
                continue
            row_res = res[i]
            row_B = B[k]
            for j in range(m):
                row_res[j] += aik * row_B[j]
    return res


def _mat_trace(A: List[List[Fraction]]) -> Fraction:
    return sum(A[i][i] for i in range(len(A)))


def _char_poly_integer(A_int: List[List[int]]) -> List[int]:
    """
    Compute the monic characteristic polynomial of an integer matrix.

    Returns coefficients [1, c1, ..., cn] such that
    p(t) = t^n + c1 t^{n-1} + ... + cn.
    """
    n = len(A_int)
    A: List[List[Fraction]] = [[Fraction(a) for a in row] for row in A_int]
    traces: List[Fraction] = []
    A_power: List[List[Fraction]] = [row[:] for row in A]
    for k in range(1, n + 1):
        if k == 1:
            A_power = [row[:] for row in A]
        else:
            A_power = _mat_mul(A_power, A)
        traces.append(_mat_trace(A_power))
    coeff_fracs: List[Fraction] = [Fraction(0)] * (n + 1)
    for k in range(1, n + 1):
        s = traces[k - 1]
        for j in range(1, k):
            s += coeff_fracs[j] * traces[k - j - 1]
        coeff_fracs[k] = -s / k
    coeffs: List[int] = [1]
    for k in range(1, n + 1):
        ck = coeff_fracs[k]
        if ck.denominator != 1:
            raise LawValidationError("spectral_geometry: characteristic polynomial has non-integer coefficients")
        coeffs.append(int(ck))
    return coeffs


def _poly_eval_int(coeffs: List[int], x: int) -> int:
    """
    Horner evaluation of an integer polynomial.
    """
    res = 0
    for a in coeffs:
        res = res * x + a
    return res


def _poly_divide_by_root(coeffs: List[int], root: int) -> List[int]:
    """
    Synthetic division of a monic polynomial by (t - root).

    coeffs represent p(t) = t^n + c1 t^{n-1} + ... + cn.
    Returns the quotient coefficients of degree n-1 in the same format.
    """
    n = len(coeffs) - 1
    out: List[int] = [coeffs[0]]
    acc = coeffs[0]
    for i in range(1, n):
        acc = coeffs[i] + root * acc
        out.append(acc)
    remainder = coeffs[-1] + root * acc
    if remainder != 0:
        raise LawValidationError("spectral_geometry: synthetic division remainder non-zero for claimed root")
    return out


def _factor_integer_roots(coeffs: List[int]) -> List[int]:
    """
    Factor a monic integer polynomial into linear factors over the integers.

    Returns the list of integer roots with multiplicity. Raises LawValidationError
    if at any step no integer root is found, which means the polynomial has
    non-rational eigenvalues.
    """
    roots: List[int] = []
    p = list(coeffs)
    while len(p) > 1:
        # Cauchy bound: all roots lie in |x| <= 1 + max_i |a_i|.
        bound = 1 + max(abs(a) for a in p[1:])
        found = False
        for r in range(-bound, bound + 1):
            if _poly_eval_int(p, r) == 0:
                roots.append(r)
                p = _poly_divide_by_root(p, r)
                found = True
                break
        if not found:
            raise LawValidationError(
                "spectral_geometry: operator has non-rational eigenvalues; "
                "spectrum not representable over rationals"
            )
    return roots


def _nullspace(matrix: List[List[Fraction]]) -> List[List[Fraction]]:
    """
    Compute a rational basis for the nullspace of a matrix.
    """
    if not matrix:
        return []
    m = len(matrix)
    n = len(matrix[0])
    A: List[List[Fraction]] = [[entry for entry in row] for row in matrix]
    pivot_cols: List[int] = []
    row = 0
    for col in range(n):
        pivot_row = None
        for r in range(row, m):
            if A[r][col] != 0:
                pivot_row = r
                break
        if pivot_row is None:
            continue
        if pivot_row != row:
            A[row], A[pivot_row] = A[pivot_row], A[row]
        pivot_cols.append(col)
        pivot_val = A[row][col]
        for j in range(col, n):
            A[row][j] /= pivot_val
        for r in range(m):
            if r == row:
                continue
            factor = A[r][col]
            if factor == 0:
                continue
            for j in range(col, n):
                A[r][j] -= factor * A[row][j]
        row += 1
        if row == m:
            break
    free_cols = [c for c in range(n) if c not in pivot_cols]
    if not free_cols:
        return []
    basis: List[List[Fraction]] = []
    for free in free_cols:
        vec = [Fraction(0) for _ in range(n)]
        vec[free] = Fraction(1)
        for r, col in enumerate(pivot_cols):
            vec[col] = -A[r][free]
        basis.append(vec)
    return basis


def _normalized_eigenpair_1x1(matrix: List[List[Fraction]]) -> Tuple[List[Fraction], List[List[Fraction]]]:
    """
    Spectral decomposition for a 1x1 operator.
    """
    lam = matrix[0][0]
    # Eigenvector is [1]; already unit norm.
    return [lam], [[Fraction(1)]]


def _normalized_eigenpair_2x2(matrix: List[List[Fraction]]) -> Tuple[List[Fraction], List[List[Fraction]]]:
    """
    Spectral decomposition for a 2x2 operator with rational spectrum.

    The algorithm:
    - compute eigenvalues via the quadratic formula,
    - require discriminant to be a perfect square rational,
    - construct a rational eigenvector for each eigenvalue,
    - normalize each eigenvector to unit norm when possible.
    """
    a, b = matrix[0]
    c, d = matrix[1]
    trace = a + d
    det = a * d - b * c
    disc = trace * trace - 4 * det
    if disc < 0:
        raise LawValidationError(
            "spectral_geometry: 2x2 operator has negative discriminant; complex spectrum not supported"
        )
    if not _is_perfect_square_fraction(disc):
        raise LawValidationError(
            "spectral_geometry: 2x2 operator must have perfect-square discriminant for rational eigenvalues"
        )
    sqrt_disc = _sqrt_fraction(disc)
    two = Fraction(2)
    lam1 = (trace + sqrt_disc) / two
    lam2 = (trace - sqrt_disc) / two

    def eigenvector_for(lam: Fraction) -> List[Fraction]:
        a1 = a - lam
        d1 = d - lam
        # Solve (A - λI)v = 0.
        if b != 0:
            v1 = Fraction(1)
            v2 = -a1 / b
        elif c != 0:
            v2 = Fraction(1)
            v1 = -d1 / c
        elif a1 == 0 and d1 == 0:
            # Scalar multiple of identity: choose basis vector.
            v1 = Fraction(1)
            v2 = Fraction(0)
        else:
            # Fallback to second row if first is degenerate.
            v2 = Fraction(1)
            v1 = -d1 / c if c != 0 else Fraction(0)
        return [v1, v2]

    def normalize(vec: List[Fraction]) -> List[Fraction]:
        norm_sq = sum(component * component for component in vec)
        if norm_sq == 0:
            raise LawValidationError("spectral_geometry: zero vector cannot serve as an eigenvector")
        if not _is_perfect_square_fraction(norm_sq):
            raise LawValidationError(
                "spectral_geometry: cannot find rational unit-normalized harmonic mode for eigenvalue"
            )
        sqrt_norm = _sqrt_fraction(norm_sq)
        return [component / sqrt_norm for component in vec]

    v1 = normalize(eigenvector_for(lam1))
    v2 = normalize(eigenvector_for(lam2))

    # Sort by eigenvalue to satisfy non-decreasing spectral weight ordering.
    pairs = sorted(zip([lam1, lam2], [v1, v2]), key=lambda p: p[0])
    weights = [lam for lam, _ in pairs]
    modes = [vec for _, vec in pairs]
    return weights, modes


def _spectral_components(matrix: List[List[Fraction]]) -> Tuple[List[Fraction], List[List[Fraction]]]:
    """
    Compute spectral weights and harmonic modes for a small rational operator matrix.

    For 1x1 and 2x2 matrices this specializes to closed-form spectral
    decompositions; for higher dimensions it computes the characteristic
    polynomial over the integers, factors it into linear terms with integer
    roots (corresponding to rational eigenvalues of the original operator),
    and constructs a full rational orthonormal eigenbasis when possible.
    """
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise LawValidationError("spectral_geometry: operator matrix must be non-empty and square")
    if n == 1:
        return _normalized_eigenpair_1x1(matrix)
    if n == 2:
        return _normalized_eigenpair_2x2(matrix)

    A_int, scale = _matrix_to_integer(matrix)
    coeffs = _char_poly_integer(A_int)
    # Integer roots of the characteristic polynomial correspond to rational
    # eigenvalues of the original matrix after dividing by the scale factor.
    integer_roots = _factor_integer_roots(coeffs)

    weights: List[Fraction] = []
    modes: List[List[Fraction]] = []
    # Build eigenvectors for each eigenvalue, enforcing a full eigenbasis.
    n_dim = n
    used_vectors = 0
    distinct_roots = sorted(set(integer_roots))
    for r in distinct_roots:
        lam = Fraction(r, scale)
        multiplicity = integer_roots.count(r)
        # Build A - λI in rational form.
        shifted: List[List[Fraction]] = []
        for i, row in enumerate(matrix):
            shifted_row: List[Fraction] = []
            for j, entry in enumerate(row):
                if i == j:
                    shifted_row.append(entry - lam)
                else:
                    shifted_row.append(entry)
            shifted.append(shifted_row)
        basis = _nullspace(shifted)
        if not basis:
            raise LawValidationError(
                "spectral_geometry: failed to construct eigenvectors for rational eigenvalue"
            )
        if len(basis) < multiplicity:
            raise LawValidationError(
                "spectral_geometry: operator not diagonalizable over rationals; "
                "insufficient eigenvectors for eigenvalue"
            )
        for vec in basis[:multiplicity]:
            norm_sq = sum(component * component for component in vec)
            if norm_sq == 0:
                raise LawValidationError("spectral_geometry: zero vector cannot serve as an eigenvector")
            if not _is_perfect_square_fraction(norm_sq):
                raise LawValidationError(
                    "spectral_geometry: cannot find rational unit-normalized harmonic mode for eigenvalue"
                )
            sqrt_norm = _sqrt_fraction(norm_sq)
            normalized_vec = [component / sqrt_norm for component in vec]
            weights.append(lam)
            modes.append(normalized_vec)
            used_vectors += 1
    if used_vectors != n_dim:
        raise LawValidationError(
            "spectral_geometry: eigenbasis incomplete; expected a full set of rational harmonic modes"
        )
    # Sort eigenpairs by eigenvalue to satisfy non-decreasing spectral weight ordering.
    pairs = sorted(zip(weights, modes), key=lambda p: p[0])
    sorted_weights = [lam for lam, _ in pairs]
    sorted_modes = [vec for _, vec in pairs]
    return sorted_weights, sorted_modes


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    spectral_geometry realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier whose elements form the recognition basis.
    flow_map:
        FlowMap carrier whose flow_table encodes a deterministic flow on that basis.

    Semantics
    ---------
    Construct the flow operator and deviation operator on the finite basis and
    compute their spectral components (weights + harmonic modes) exactly over
    rational scalars, emitting a `spectral_geometry` carrier that satisfies
    the Av = λv laws enforced by `validate_spectral_geometry`:

    - basis = sorted flow_map.elements,
    - operator_matrices = { "flow": F, "deviation": L = I - F },
    - spectral_weights / harmonic_modes tables for both operators, with
      spectral weights sorted in non-decreasing order and harmonic modes
      unit-normalized.
    """
    profile = inputs.get("profile_topos")
    flow_map = inputs.get("flow_map")
    if profile is None or flow_map is None:
        raise KeyError("spectral_geometry requires 'profile_topos' and 'flow_map' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("spectral_geometry profile_topos input must have kind 'profile_topos'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("spectral_geometry flow_map input must have kind 'flow_map'")

    # Ensure the flow_map is defined over the given profile_topos.
    carrier_id = flow_map.get("carrier_id")
    if carrier_id is not None and carrier_id != profile["id"]:
        raise LawValidationError(
            "spectral_geometry: flow_map.carrier_id must match profile_topos.id when provided"
        )
    profile_elements = set(profile.get("elements", []))
    if profile_elements:
        if not set(flow_map.get("elements", [])).issubset(profile_elements):
            raise LawValidationError(
                "spectral_geometry: flow_map.elements must be a subset of profile_topos.elements"
            )

    basis, flow_matrix_frac, deviation_matrix_frac = _fraction_flow_matrices(flow_map)

    flow_weights, flow_modes = _spectral_components(flow_matrix_frac)
    deviation_weights, deviation_modes = _spectral_components(deviation_matrix_frac)

    operator_matrices = {
        "flow": [
            [fraction_to_canonical_string(entry) for entry in row] for row in flow_matrix_frac
        ],
        "deviation": [
            [fraction_to_canonical_string(entry) for entry in row] for row in deviation_matrix_frac
        ],
    }
    spectral_weights = {
        "flow": [fraction_to_canonical_string(value) for value in flow_weights],
        "deviation": [fraction_to_canonical_string(value) for value in deviation_weights],
    }
    harmonic_modes = {
        "flow": [
            [fraction_to_canonical_string(component) for component in vec] for vec in flow_modes
        ],
        "deviation": [
            [fraction_to_canonical_string(component) for component in vec] for vec in deviation_modes
        ],
    }

    payload = {
        "kind": "spectral_geometry",
        "basis": basis,
        "operator_matrices": operator_matrices,
        "spectral_weights": spectral_weights,
        "harmonic_modes": harmonic_modes,
        "act_ref": "SpectralGeometry",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "spectral_geometry",
            "src": profile["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "spectral_geometry",
            "src": flow_map["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"spectral_geometry": payload["id"]},
    )
