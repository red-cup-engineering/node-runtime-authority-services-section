from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class SeedValuePayload(RecognitionPayload):
    """Payload for the ``seed-value`` act.

    Records an initial value payload, reflecting
    `(HeadTrace Normalization)`.
    """

    payload: Any = Field(
        ...,
        description="Raw payload of the seeded value",
    )

