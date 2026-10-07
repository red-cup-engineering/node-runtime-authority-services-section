from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class MeetWitness(RecognitionPayload):
    """Payload for a meet-recognition fibre.

    Records the identifiers of the two input recognitions and the
    shared act footprint that approximates their greatest lower bound.
    """

    left_id: str = Field(..., description="Identifier of the left recognition")
    right_id: str = Field(..., description="Identifier of the right recognition")
    shared_acts: List[str] = Field(
        default_factory=list,
        description="Sorted list of shared acts between left and right",
    )

