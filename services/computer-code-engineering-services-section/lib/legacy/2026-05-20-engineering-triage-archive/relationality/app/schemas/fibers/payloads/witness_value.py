from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class WitnessValuePayload(RecognitionPayload):
    """Payload for the ``witness-value`` act.

    Records that a value recognition witnesses normalization, reflecting
    `(RecognizeValue Normalization)`.
    """

    target_id: str = Field(..., description="Identifier of the value target")
    judgement_type: Literal["value"] = Field(
        default="value",
        description="Judgement type for this witness",
    )

