from __future__ import annotations

from typing import Any, Dict, List

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class HeadTracePayload(RecognitionPayload):
    """Payload for the ``head-trace`` act.

    Records the head segment of a trace, reflecting
    `(LeadEntry CompleteTrace)`.
    """

    trace_id: str = Field(..., description="Identifier of the source trace")
    count: int = Field(..., description="Number of head steps extracted")
    steps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Head steps of the trace in order",
    )


class TailTracePayload(RecognitionPayload):
    """Payload for the ``tail-trace`` act.

    Records the tail segment of a trace, reflecting
    `(TrailEntry CompleteTrace)`.
    """

    trace_id: str = Field(..., description="Identifier of the source trace")
    count: int = Field(..., description="Number of tail steps extracted")
    steps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tail steps of the trace in order",
    )

