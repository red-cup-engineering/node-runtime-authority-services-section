from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class ImplicationWitness(RecognitionPayload):
    """Payload for an imply-recognition fibre.

    Records the identifiers of the premise and conclusion recognitions and
    the acts that the conclusion contributes beyond the premise.
    """

    premise_id: str = Field(..., description="Identifier of the premise recognition")
    conclusion_id: str = Field(
        ..., description="Identifier of the conclusion recognition"
    )
    added_acts: List[str] = Field(
        default_factory=list,
        description="Sorted list of acts present in the conclusion but not the premise",
    )

