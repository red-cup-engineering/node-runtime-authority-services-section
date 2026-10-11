from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class WitnessObservationPayload(RecognitionPayload):
    """Payload for the ``witness-observation`` act.

    Records that an observation recognition witnesses contextual
    indistinguishability, reflecting `(RecognizeObservation EquateContexts)`.
    """

    target_id: str = Field(..., description="Identifier of the observed target")
    judgement_type: Literal["observation"] = Field(
        default="observation",
        description="Judgement type for this witness",
    )

