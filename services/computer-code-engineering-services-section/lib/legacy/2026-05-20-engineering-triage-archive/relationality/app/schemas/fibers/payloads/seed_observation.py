from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class SeedObservationPayload(RecognitionPayload):
    """Payload for the ``seed-observation`` act.

    Records an initial observation payload, reflecting
    `(HeadTrace EquateContexts)`.
    """

    payload: Any = Field(
        ...,
        description="Raw payload of the seeded observation",
    )

