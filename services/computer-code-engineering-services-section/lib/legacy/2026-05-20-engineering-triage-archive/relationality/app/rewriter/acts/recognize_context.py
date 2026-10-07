from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RecognizeContextHandler(ActHandler):
    """Per-act handler for ``recognize-context``."""

    acts = ["recognize-context"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        value = context.get_input("value")
        observation_id = context.get_input("observation_id")

        if value is None and observation_id is None:
            return HandlerResult.fail("Missing required input: value or observation_id")

        recognition_id = uuid4()
        recognition = {
            "id": str(recognition_id),
            "type": "judgement",
            "title": "Recognition (context)",
            "act": act,
            "acts": [act],
            "value": value,
            "source_observation": observation_id,
            "recognized_at": datetime.utcnow().isoformat(),
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={"recognition_id": str(persisted_id), "recognition": recognition},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

