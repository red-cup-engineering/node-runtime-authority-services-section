"""
Utilities for constructing Observation carriers.

Observations are the I/O boundary of the relational machine.  To keep them
lawful and consistent, all construction of ``kind: "observation"`` payloads
should go through :func:`record_observation` rather than ad-hoc dicts.
"""

from __future__ import annotations

from typing import Any, MutableMapping, Mapping

from .law_enforcement import validate_raw_object


def record_observation(
    *,
    carrier_id: str,
    measurement_frame_id: str,
    element: str,
    act_ref: str,
    term_id: str | None = None,
    judgment_id: str | None = None,
    diagnostics: MutableMapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """
    Construct a schema- and law-valid Observation carrier.

    This helper:
    - enforces the Observation shape (required fields and kinds),
    - applies canonical JSON hashing to populate ``id``, and
    - optionally appends a lightweight diagnostic record into the provided
      ``diagnostics`` mapping.

    The returned payload is suitable for insertion into a RelationalGraph
    or for use as a realizer output node.
    """
    payload: dict[str, Any] = {
        "kind": "observation",
        "carrier_id": carrier_id,
        "measurement_frame_id": measurement_frame_id,
        "element": element,
        "act_ref": act_ref,
    }
    if term_id is not None:
        payload["term_id"] = term_id
    if judgment_id is not None:
        payload["judgment_id"] = judgment_id

    # Canonicalize and validate against the Observation schema.
    validate_raw_object(payload)

    if diagnostics is not None:
        observations = diagnostics.setdefault("observations", [])
        observations.append(
            {
                "observation_id": payload["id"],
                "act_ref": act_ref,
                "carrier_id": carrier_id,
                "measurement_frame_id": measurement_frame_id,
            }
        )

    return payload


__all__ = ["record_observation"]

