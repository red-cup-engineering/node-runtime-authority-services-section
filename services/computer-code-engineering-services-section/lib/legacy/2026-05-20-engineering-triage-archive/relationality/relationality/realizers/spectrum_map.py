from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence, fraction_to_canonical_string
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError
from .spectral_geometry import _fraction_flow_matrices, _spectral_components


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    spectrum_map realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the finite judgment lattice.
    flow_map:
        FlowMap carrier whose flow_table defines a deterministic temporal
        operator on that lattice.

    Semantics
    ---------
    Compute the spectral decomposition of the flow operator F on the finite
    basis, emitting a ``spectral_geometry`` carrier with a single operator
    entry ``\"flow\"``:

    - basis = sorted flow_map.elements,
    - operator_matrices = { "flow": F },
    - spectral_weights / harmonic_modes for F with non-decreasing weights
      and unit-normalized modes.
    """
    profile = inputs.get("profile_topos")
    flow_map = inputs.get("flow_map")
    if profile is None or flow_map is None:
        raise KeyError("spectrum_map requires 'profile_topos' and 'flow_map' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("spectrum_map profile_topos input must have kind 'profile_topos'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("spectrum_map flow_map input must have kind 'flow_map'")

    carrier_id = flow_map.get("carrier_id")
    if carrier_id is not None and carrier_id != profile["id"]:
        raise LawValidationError(
            "spectrum_map: flow_map.carrier_id must match profile_topos.id when provided"
        )
    profile_elements = set(profile.get("elements", []))
    if profile_elements:
        if not set(flow_map.get("elements", [])).issubset(profile_elements):
            raise LawValidationError(
                "spectrum_map: flow_map.elements must be a subset of profile_topos.elements"
            )

    basis, flow_matrix_frac, _deviation_matrix_frac = _fraction_flow_matrices(flow_map)
    flow_weights, flow_modes = _spectral_components(flow_matrix_frac)

    operator_matrices = {
        "flow": [
            [fraction_to_canonical_string(entry) for entry in row]
            for row in flow_matrix_frac
        ],
    }
    spectral_weights = {
        "flow": [fraction_to_canonical_string(value) for value in flow_weights],
    }
    harmonic_modes = {
        "flow": [
            [fraction_to_canonical_string(component) for component in vec]
            for vec in flow_modes
        ],
    }

    payload = {
        "kind": "spectral_geometry",
        "basis": basis,
        "operator_matrices": operator_matrices,
        "spectral_weights": spectral_weights,
        "harmonic_modes": harmonic_modes,
        "act_ref": "SpectrumMap",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "spectrum_map",
            "src": profile["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "spectrum_map",
            "src": flow_map["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"spectral_geometry": payload["id"]},
    )

