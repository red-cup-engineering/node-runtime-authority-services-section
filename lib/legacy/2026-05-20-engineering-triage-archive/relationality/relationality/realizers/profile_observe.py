from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_observe realizer.

    Inputs
    ------
    observation_carrier:
        External ObservationCarrier node (kind ``observation_carrier``).
    profile_topos:
        ProfileTopos node (kind ``profile_topos``) providing the judgment
        lattice in which the observation is interpreted.
    measurement_frame:
        MeasurementFrame node (kind ``measurement_frame``) specifying which
        observation carriers are admissible.

    Semantics
    ---------
    Diagnostic check for admissibility of an ObservationCarrier for a given
    profile and measurement frame (ProfileObserve/RecognizeObservation):

    - When measurement_frame.admissible_observations is non-empty, the
      observation_carrier.id must appear in that list.
    - When admissible_observations is empty, the carrier is treated as
      admissible by default.

    Emits profile_observe_evidence recording the IDs and a status flag; on
    failure, a structured counterexample is included.
    """
    carrier = inputs.get("observation_carrier")
    profile_topos = inputs.get("profile_topos")
    measurement_frame = inputs.get("measurement_frame")
    if carrier is None or profile_topos is None or measurement_frame is None:
        raise KeyError(
            "profile_observe requires 'observation_carrier', 'profile_topos', and 'measurement_frame' inputs"
        )
    if carrier.get("kind") != "observation_carrier":
        raise LawValidationError("profile_observe observation_carrier input must have kind 'observation_carrier'")
    if profile_topos.get("kind") != "profile_topos":
        raise LawValidationError("profile_observe profile_topos input must have kind 'profile_topos'")
    if measurement_frame.get("kind") != "measurement_frame":
        raise LawValidationError("profile_observe measurement_frame input must have kind 'measurement_frame'")

    admissible = measurement_frame.get("admissible_observations", [])
    carrier_id = carrier.get("id")
    if not isinstance(carrier_id, str):
        raise LawValidationError("profile_observe requires observation_carrier.id to be a string")

    status = "pass"
    counterexample = None
    if admissible and carrier_id not in admissible:
        status = "fail"
        counterexample = {
            "reason": "observation_carrier.id not in measurement_frame.admissible_observations",
            "observation_carrier_id": carrier_id,
            "admissible_observations": list(admissible),
        }

    evidence = {
        "kind": "profile_observe_evidence",
        "observation_carrier_id": carrier_id,
        "profile_topos_id": profile_topos["id"],
        "measurement_frame_id": measurement_frame["id"],
        "status": status,
        "act_ref": "ProfileObserve",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "profile_observe",
            "src": carrier_id,
            "tgt": evidence["id"],
        },
        {
            "operator": "profile_observe",
            "src": profile_topos["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "profile_observe",
            "src": measurement_frame["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"profile_observe_evidence": evidence["id"]},
    )

