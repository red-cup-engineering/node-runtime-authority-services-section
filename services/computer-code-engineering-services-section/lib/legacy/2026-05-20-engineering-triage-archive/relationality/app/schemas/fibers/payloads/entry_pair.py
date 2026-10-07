from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.fibers.payloads.recognition_ref import RecognitionRef


class EntryPairPayload(RecognitionPayload):
    """Payload for the ``entry`` act.

    Captures the two-place structure of an entry, including the
    recognitions and/or payloads occupying the left and right
    positions.
    """

    left_recognition: Optional[RecognitionRef] = Field(
        default=None, description="Reference to the left recognition, if provided"
    )
    right_recognition: Optional[RecognitionRef] = Field(
        default=None, description="Reference to the right recognition, if provided"
    )
    left: Optional[Dict[str, Any]] = Field(
        default=None, description="Inline payload for the left position"
    )
    right: Optional[Dict[str, Any]] = Field(
        default=None, description="Inline payload for the right position"
    )
