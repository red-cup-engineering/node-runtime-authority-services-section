from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.fibers.payloads.recognition_ref import RecognitionRef


class RecognitionPair(RecognitionPayload):
    """Payload for the ``recognition`` act.

    Captures the two-place structure of a recognition, optionally
    including inline payloads and/or identifiers for each side.
    """

    left_ref: Optional[RecognitionRef] = Field(
        default=None, description="Reference for the left recognition, if any"
    )
    right_ref: Optional[RecognitionRef] = Field(
        default=None, description="Reference for the right recognition, if any"
    )
    left: Optional[Dict[str, Any]] = Field(
        default=None, description="Inline payload for the left position"
    )
    right: Optional[Dict[str, Any]] = Field(
        default=None, description="Inline payload for the right position"
    )
