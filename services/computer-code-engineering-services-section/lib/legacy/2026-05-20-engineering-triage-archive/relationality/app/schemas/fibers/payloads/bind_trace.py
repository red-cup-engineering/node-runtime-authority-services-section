from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class BindTracePayload(RecognitionPayload):
    """Payload for the ``bind-trace`` act.

    Records that the head of a trace has been named, reflecting
    `(FirstName HeadTrace)`.
    """

    trace_id: str = Field(..., description="Identifier of the trace being bound")
    name: str = Field(..., description="Name bound to the head of the trace")
    binding: Dict[str, Any] = Field(
        ..., description="Binding payload attached at the head"
    )

