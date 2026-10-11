from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class RenewContextPayload(RecognitionPayload):
    """Payload for the ``renew-context`` act.

    Records that a seeded context has been extended and reattached to
    a contextualized trace, reflecting `(ExtendFirstContext ContextualizeTrace)`.
    """

    context_id: str = Field(
        ..., description="Identifier of the context being renewed"
    )
    trace_id: str = Field(
        ..., description="Identifier of the trace being reattached"
    )
    name: str = Field(..., description="Name bound in the renewed context")
    bindings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Bindings present in the renewed context",
    )
    status: str = Field(..., description="Status of the contextualized trace")

