from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.stlc import TypeAST


class TypeFamilyPayload(RecognitionPayload):
    """Payload for the ``construct-types`` / ``collect-types`` acts.

    Represents a finite family of STLC types built from recognition
    lattice witnesses (meet/join/imply).
    """

    types: List[TypeAST] = Field(
        default_factory=list,
        description="Family of STLC types in this constructed/collected set",
    )

