from __future__ import annotations

from typing import Any, List, Optional

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.fibers.payloads.recognition_ref import RecognitionRef


class GroundRecognitionPayload(RecognitionPayload):
    """Payload for the ``ground-recognition`` act.

    Encodes the bottom element: a recognition paired with Nothing.
    """

    kind: str = Field(
        default="ground",
        description="Marker indicating this is the bottom recognition",
    )
    content: Optional[Any] = Field(
        default=None,
        description="Ground content (typically None to represent absence)",
    )


class CapRecognitionPayload(RecognitionPayload):
    """Payload for the ``cap-recognition`` act.

    Encodes a maximal recognition witnessing a collection of traces.
    """

    kind: str = Field(
        default="cap",
        description="Marker indicating this is the top recognition",
    )
    traces: List[RecognitionRef] = Field(
        default_factory=list,
        description="References to trace recognitions witnessed by this cap",
    )
    traces_count: int = Field(
        default=0,
        description="Number of traces recorded in this cap",
    )
