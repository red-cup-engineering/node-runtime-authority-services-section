from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SeedTermHandler(ActHandler):
    """Per-act handler for ``seed-term``."""

    acts = ["seed-term"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        payload = context.get_input("payload")
        if payload is None:
            return HandlerResult.fail("Missing required input: payload")

        observation_id = uuid4()
        observation = {
            "id": str(observation_id),
            "type": "observation",
            "title": "Seeded term",
            "act": act,
            "acts": [act],
            "payload": payload,
            "seeded_at": datetime.utcnow().isoformat(),
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(observation)

        return HandlerResult.ok(
            outputs={"observation_id": str(persisted_id), "observation": observation},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

