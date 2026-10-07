from __future__ import annotations

from fractions import Fraction
from typing import Dict, List

from relationality.canonical import ensure_id_coherence, fraction_to_canonical_string
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError
from .spectral_geometry import _spectral_components, _mat_mul


def _to_fraction_matrix(matrix: List[List[object]]) -> List[List[Fraction]]:
    if not isinstance(matrix, list) or not matrix:
        raise LawValidationError("wave_operator: diffusion operator matrix must be a non-empty list of rows")
    frac_matrix: List[List[Fraction]] = []
    row_len: int | None = None
    for row in matrix:
        if not isinstance(row, list) or not row:
            raise LawValidationError("wave_operator: each diffusion row must be a non-empty list")
        if row_len is None:
            row_len = len(row)
        elif len(row) != row_len:
            raise LawValidationError("wave_operator: diffusion matrix rows must all have the same length")
        frac_matrix.append([Fraction(str(entry)) for entry in row])
    return frac_matrix


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    wave_operator realizer.

    Inputs
    ------
    spectral_geometry:
        SpectralGeometry carrier containing a diffusion operator matrix
        (kind ``spectral_geometry``, operator_matrices[\"diffusion\"] present).
    harmonic_modes:
        SpectralGeometry carrier produced by harmonic_mode realizer, providing
        harmonic modes on the same basis.

    Semantics
    ---------
    Acts: WaveOperator = (DiffuseFixedFlowProfile HarmonicMode).

    We interpret this as second-order dynamics obtained by iterating the
    diffusion operator. Concretely, we construct a wave operator

        W = H^2

    on the common basis, where H is the diffusion operator. We then compute
    the spectral decomposition of W and emit a spectral_geometry carrier with
    a single operator entry \"wave\".

    The harmonic_modes input is used to enforce basis alignment; its modes are
    not altered here.
    """
    diffusion_spec = inputs.get("spectral_geometry") or inputs.get("diffusion_operator")
    harmonic_spec = inputs.get("harmonic_modes")
    if diffusion_spec is None or harmonic_spec is None:
        raise KeyError("wave_operator requires 'spectral_geometry' and 'harmonic_modes' inputs")
    if diffusion_spec.get("kind") != "spectral_geometry":
        raise LawValidationError("wave_operator spectral_geometry input must have kind 'spectral_geometry'")
    if harmonic_spec.get("kind") != "spectral_geometry":
        raise LawValidationError("wave_operator harmonic_modes input must have kind 'spectral_geometry'")

    basis = list(diffusion_spec.get("basis", []))
    if not basis:
        raise LawValidationError("wave_operator: diffusion spectral_geometry basis must be non-empty")
    if basis != list(harmonic_spec.get("basis", [])):
        raise LawValidationError("wave_operator requires harmonic_modes basis to match diffusion basis exactly")

    op_mats = diffusion_spec.get("operator_matrices") or {}
    diffusion_matrix = op_mats.get("diffusion")
    if diffusion_matrix is None:
        raise LawValidationError(
            "wave_operator: spectral_geometry.operator_matrices must contain 'diffusion' operator"
        )

    H_frac = _to_fraction_matrix(diffusion_matrix)
    n = len(H_frac)
    if any(len(row) != n for row in H_frac):
        raise LawValidationError("wave_operator: diffusion operator matrix must be square")

    # Wave operator W = H^2.
    W_frac = _mat_mul(H_frac, H_frac)

    weights, modes = _spectral_components(W_frac)

    operator_matrices = {
        "wave": [
            [fraction_to_canonical_string(entry) for entry in row] for row in W_frac
        ],
    }
    spectral_weights = {
        "wave": [fraction_to_canonical_string(value) for value in weights],
    }
    harmonic_modes = {
        "wave": [
            [fraction_to_canonical_string(component) for component in vec]
            for vec in modes
        ],
    }

    payload = {
        "kind": "spectral_geometry",
        "basis": basis,
        "operator_matrices": operator_matrices,
        "spectral_weights": spectral_weights,
        "harmonic_modes": harmonic_modes,
        "act_ref": "WaveOperator",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "wave_operator",
            "src": diffusion_spec["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "wave_operator",
            "src": harmonic_spec["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"wave_operator": payload["id"]},
    )
