from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class ExtendFirstContextPayload(RecognitionPayload):
    """Payload for the ``extend-first-context`` act.

    Records that the initial seeded context has been extended by
    attaching an additional binding, reflecting `(BindTrace SeedFirstContext)`.
    """

    context_id: str = Field(
        ..., description="Identifier of the seeded context being extended"
    )
    name: str = Field(..., description="Name of the new binding")
    binding: Dict[str, Any] = Field(
        ..., description="Binding payload attached to the seeded context"
    )
    bindings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resulting bindings after extension",
    )
    context_type: str = Field(
        default="evaluation",
        description="Kind of context (evaluation, proof, ...)",
    )

