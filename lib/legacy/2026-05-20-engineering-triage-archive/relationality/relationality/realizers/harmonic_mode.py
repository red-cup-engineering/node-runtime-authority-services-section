from __future__ import annotations

from fractions import Fraction
from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _select_harmonic_indices(weights: List[object]) -> List[int]:
    indices: List[int] = []
    for idx, raw in enumerate(weights):
        value = Fraction(str(raw))
        if abs(value) == Fraction(1):
            indices.append(idx)
    return indices


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    harmonic_mode realizer.

    Input
    -----
    spectral_geometry:
        SpectralGeometry carrier providing spectral weights and harmonic
        modes for at least one operator.

    Semantics
    ---------
    Extract the harmonic modes corresponding to unit-modulus spectral
    weights (|λ| = 1) for a chosen operator and package them into a new
    ``spectral_geometry`` carrier with a canonical identity operator
    ``\"harmonic_mode\"``:

    - basis is inherited from the input spectral_geometry,
    - operator_matrices.harmonic_mode is the identity on that basis,
    - spectral_weights.harmonic_mode lists 1 for each selected mode,
    - harmonic_modes.harmonic_mode lists the selected unit-normalized
      modes.
    """
    spectral = inputs.get("spectral_geometry")
    if spectral is None:
        raise KeyError("harmonic_mode requires 'spectral_geometry' input")
    if spectral.get("kind") != "spectral_geometry":
        raise LawValidationError("harmonic_mode spectral_geometry input must have kind 'spectral_geometry'")

    basis = list(spectral.get("basis", []))
    if not basis:
        raise LawValidationError("harmonic_mode: spectral_geometry basis must be non-empty")
    op_mats = spectral.get("operator_matrices") or {}
    weights_all = spectral.get("spectral_weights") or {}
    modes_all = spectral.get("harmonic_modes") or {}
    if not op_mats or not weights_all or not modes_all:
        raise LawValidationError("harmonic_mode: spectral_geometry must provide operator matrices and spectra")

    # Choose an operator deterministically (first key in sorted order).
    op_name = sorted(op_mats.keys())[0]
    weights = list(weights_all.get(op_name) or [])
    modes = list(modes_all.get(op_name) or [])
    if not weights or len(weights) != len(modes):
        raise LawValidationError("harmonic_mode: spectral_weights and harmonic_modes must be non-empty and aligned")

    indices = _select_harmonic_indices(weights)
    if not indices:
        raise LawValidationError("harmonic_mode: no unit-modulus spectral weights found")

    selected_modes: List[List[object]] = [modes[i] for i in indices]
    n = len(basis)
    # Identity operator on the basis.
    identity_matrix: List[List[str]] = []
    for i in range(n):
        row: List[str] = []
        for j in range(n):
            row.append("1" if i == j else "0")
        identity_matrix.append(row)

    operator_matrices = {
        "harmonic_mode": identity_matrix,
    }
    spectral_weights = {
        "harmonic_mode": ["1" for _ in selected_modes],
    }
    harmonic_modes = {
        "harmonic_mode": selected_modes,
    }

    payload = {
        "kind": "spectral_geometry",
        "basis": basis,
        "operator_matrices": operator_matrices,
        "spectral_weights": spectral_weights,
        "harmonic_modes": harmonic_modes,
        "act_ref": "HarmonicMode",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "harmonic_mode",
            "src": spectral["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"spectral_geometry": payload["id"]},
    )

