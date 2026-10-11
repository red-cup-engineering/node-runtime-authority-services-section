from __future__ import annotations

from fractions import Fraction
from typing import Dict, List

from relationality.canonical import ensure_id_coherence, fraction_to_canonical_string
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError
from .spectral_geometry import _spectral_components


def _to_fraction_matrix(matrix: List[List[object]]) -> List[List[Fraction]]:
    if not isinstance(matrix, list) or not matrix:
        raise LawValidationError("diffuse_fixed_flow_profile: operator matrix must be a non-empty list of rows")
    frac_matrix: List[List[Fraction]] = []
    row_len: int | None = None
    for row in matrix:
        if not isinstance(row, list) or not row:
            raise LawValidationError("diffuse_fixed_flow_profile: each row must be a non-empty list")
        if row_len is None:
            row_len = len(row)
        elif len(row) != row_len:
            raise LawValidationError("diffuse_fixed_flow_profile: matrix rows must all have the same length")
        frac_matrix.append([Fraction(str(entry)) for entry in row])
    return frac_matrix


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    diffuse_fixed_flow_profile realizer.

    Input
    -----
    spectral_geometry:
        SpectralGeometry carrier containing a deviation operator matrix.

    Semantics
    ---------
    Given a deviation operator L on a finite basis (as produced by the
    MeasureDeviationObservationKernel / deviation operator acts), construct
    a discrete diffusion operator H = I - L and compute its spectral
    decomposition exactly over the rationals, emitting a ``spectral_geometry``
    carrier with a single operator entry ``\"diffusion\"`` satisfying Av = λv.
    """
    spectral = inputs.get("spectral_geometry")
    deviation = inputs.get("deviation_operator")
    if spectral is None and deviation is None:
        raise KeyError(
            "diffuse_fixed_flow_profile requires 'spectral_geometry' or 'deviation_operator' input"
        )

    if spectral is not None:
        if spectral.get("kind") != "spectral_geometry":
            raise LawValidationError(
                "diffuse_fixed_flow_profile spectral_geometry input must have kind 'spectral_geometry'"
            )
        basis = list(spectral.get("basis", []))
        if not basis:
            raise LawValidationError("diffuse_fixed_flow_profile: spectral_geometry basis must be non-empty")
        op_mats = spectral.get("operator_matrices") or {}
        deviation_matrix = op_mats.get("deviation")
        if deviation_matrix is None:
            raise LawValidationError(
                "diffuse_fixed_flow_profile: spectral_geometry.operator_matrices must contain 'deviation' operator"
            )
        src_id = spectral["id"]
    else:
        if deviation.get("kind") != "deviation_operator":
            raise LawValidationError(
                "diffuse_fixed_flow_profile deviation_operator input must have kind 'deviation_operator'"
            )
        basis = list(deviation.get("basis", []))
        if not basis:
            raise LawValidationError("diffuse_fixed_flow_profile: deviation_operator basis must be non-empty")
        deviation_matrix = deviation.get("operator_matrix")
        if deviation_matrix is None:
            raise LawValidationError("diffuse_fixed_flow_profile: deviation_operator.operator_matrix is required")
        src_id = deviation["id"]

    L_frac = _to_fraction_matrix(deviation_matrix)
    n = len(L_frac)
    if any(len(row) != n for row in L_frac):
        raise LawValidationError("diffuse_fixed_flow_profile: deviation operator matrix must be square")

    # Discrete diffusion operator H = I - L.
    heat_matrix_frac: List[List[Fraction]] = []
    for i in range(n):
        row: List[Fraction] = []
        for j in range(n):
            value = (Fraction(1) if i == j else Fraction(0)) - L_frac[i][j]
            row.append(value)
        heat_matrix_frac.append(row)

    heat_weights, heat_modes = _spectral_components(heat_matrix_frac)

    operator_matrices = {
        "diffusion": [
            [fraction_to_canonical_string(entry) for entry in row]
            for row in heat_matrix_frac
        ],
    }
    spectral_weights = {
        "diffusion": [fraction_to_canonical_string(value) for value in heat_weights],
    }
    harmonic_modes = {
        "diffusion": [
            [fraction_to_canonical_string(component) for component in vec]
            for vec in heat_modes
        ],
    }

    payload = {
        "kind": "spectral_geometry",
        "basis": basis,
        "operator_matrices": operator_matrices,
        "spectral_weights": spectral_weights,
        "harmonic_modes": harmonic_modes,
        "act_ref": "DiffuseFixedFlowProfile",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "diffuse_fixed_flow_profile",
            "src": src_id,
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"diffusion_operator": payload["id"]},
    )
