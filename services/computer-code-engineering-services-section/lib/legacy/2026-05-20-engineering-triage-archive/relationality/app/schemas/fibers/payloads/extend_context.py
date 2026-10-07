from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class ExtendContextPayload(RecognitionPayload):
    """Payload for the ``extend-context`` act.

    Records that a renewed context has been extended by attaching
    additional bindings, reflecting `(BindTrace RenewContext)`.
    """

    parent_context_id: str = Field(
        ..., description="Identifier of the parent context being extended"
    )
    bindings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Merged bindings after extension",
    )
    context_type: str = Field(
        default="evaluation",
        description="Kind of context (evaluation, proof, ...)",
    )
    depth: int = Field(
        ..., description="Depth of the extended context in the chain",
    )

