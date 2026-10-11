from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class JoinWitness(RecognitionPayload):
    """Payload for a join-recognition fibre.

    Records the identifiers of the two input recognitions and the
    union act footprint that approximates their least upper bound.
    """

    left_id: str = Field(..., description="Identifier of the left recognition")
    right_id: str = Field(..., description="Identifier of the right recognition")
    union_acts: List[str] = Field(
        default_factory=list,
        description="Sorted list of union acts between left and right",
    )

