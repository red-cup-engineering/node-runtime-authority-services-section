from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class WitnessPayload(RecognitionPayload):
    """Payload for the ``witness`` act.

    Records the generic witness relationship `(NotRelate Relate)`.
    """

    kind: Literal["witness"] = Field(
        default="witness",
        description="Marker indicating generic witness between relate and not-relate",
    )

