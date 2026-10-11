from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.stlc import TermAST


class TermFamilyPayload(RecognitionPayload):
    """Payload for the ``construct-terms`` / ``collect-terms`` acts.

    Represents a finite family of STLC terms built from the term
    formers.
    """

    terms: List[TermAST] = Field(
        default_factory=list,
        description="Family of STLC terms in this constructed/collected set",
    )

