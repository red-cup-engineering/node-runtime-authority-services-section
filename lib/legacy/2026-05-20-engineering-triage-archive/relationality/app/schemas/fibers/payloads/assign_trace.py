from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class AssignTracePayload(RecognitionPayload):
    """Payload for the ``assign-trace`` act.

    Records that a name has been propagated along a trace tail,
    reflecting `(BindTrace TailTrace)`.
    """

    trace_id: str = Field(..., description="Identifier of the trace being assigned")
    name: str = Field(..., description="Name assigned along the trace")
    assignment: Dict[str, Any] = Field(
        ..., description="Assignment payload attached to the trace"
    )

