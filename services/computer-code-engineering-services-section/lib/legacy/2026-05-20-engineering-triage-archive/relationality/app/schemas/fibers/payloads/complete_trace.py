from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class CompleteTracePayload(RecognitionPayload):
    """Payload for the ``complete-trace`` act.

    Records that a trace has been completed with an optional result,
    reflecting `(StartTrace AdvanceTrace)`.
    """

    trace_id: str = Field(..., description="Identifier of the completed trace")
    status: str = Field(..., description="Final status of the trace")
    result: Dict[str, Any] | None = Field(
        default=None,
        description="Optional result payload attached at completion",
    )

