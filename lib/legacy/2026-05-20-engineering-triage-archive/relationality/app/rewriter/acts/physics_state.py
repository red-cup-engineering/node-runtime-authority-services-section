from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.physics import PhysicsState


class PhysicsStateHandler(ActHandler):
    """Handler for the ``physics-state`` act.

    Wraps a collection of recognitions at a profile into a PhysicsState.
    """

    acts = ["physics-state"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition_ids = context.get_input("recognition_ids", [])
        profile_id = context.get_input("profile_id")

        state = PhysicsState(
            id=str(uuid4()),
            profile_id=profile_id,
            recognition_ids=[str(rid) for rid in recognition_ids],
            metadata={
                "trace_id": trace_id,
                "constructed_at": now,
            },
        )

        return HandlerResult.ok(
            outputs={"state": state.model_dump()},
            metadata={"act": act},
        )

