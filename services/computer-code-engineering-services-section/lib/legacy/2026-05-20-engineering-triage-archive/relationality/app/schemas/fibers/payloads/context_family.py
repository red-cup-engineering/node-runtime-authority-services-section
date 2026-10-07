from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.stlc import TypingContext


class ContextFamilyPayload(RecognitionPayload):
    """Payload for the ``construct-contexts`` / ``collect-contexts`` acts.

    Represents a finite family of typing contexts.
    """

    contexts: List[TypingContext] = Field(
        default_factory=list,
        description="Family of typing contexts recorded by this act",
    )

