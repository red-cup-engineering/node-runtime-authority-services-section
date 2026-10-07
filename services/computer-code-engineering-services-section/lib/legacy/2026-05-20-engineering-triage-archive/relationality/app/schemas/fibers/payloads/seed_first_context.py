from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class SeedFirstContextPayload(RecognitionPayload):
    """Payload for the ``seed-first-context`` act.

    Records that an initial context is seeded by anchoring a named,
    contextualized trace back to the primordial witness *Nothing*.
    """

    trace_id: str = Field(..., description="Identifier of the anchored trace")
    name: str = Field(..., description="Name bound in the seeded context")
    bindings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Initial bindings of the seeded context",
    )
    context_type: str = Field(
        default="evaluation",
        description="Kind of context being seeded (evaluation, proof, ...)",
    )
    status: str = Field(..., description="Status of the anchored trace")

