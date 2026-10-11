from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class ContextualizedTracePayload(RecognitionPayload):
    """Payload for the ``contextualize-trace`` act.

    Records that a named assignment encloses a completed trace.
    """

    trace_id: str = Field(..., description="Identifier of the underlying trace")
    name: str = Field(..., description="Name of the assignment")
    assignment: Dict[str, Any] = Field(
        ..., description="Assignment payload for the given name"
    )
    status: str = Field(..., description="Status of the completed trace")

