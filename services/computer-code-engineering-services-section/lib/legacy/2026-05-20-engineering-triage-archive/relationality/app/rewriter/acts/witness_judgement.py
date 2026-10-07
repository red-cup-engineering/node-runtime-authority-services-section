from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class WitnessJudgementHandler(ActHandler):
    """Per-act handler for ``witness-judgement``."""

    acts = ["witness-judgement"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        target_id = context.get_input("target_id")
        judgement_type = context.get_input("judgement_type", "observation")

        if target_id is None:
            return HandlerResult.fail("Missing required input: target_id")

        witness_id = uuid4()
        witness = {
            "id": str(witness_id),
            "type": "witness",
            "title": "Witness (judgement)",
            "act": act,
            "acts": [act],
            "target_id": target_id,
            "judgement_type": judgement_type,
            "witnessed_at": datetime.utcnow().isoformat(),
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(witness)

        return HandlerResult.ok(
            outputs={"witness_id": str(persisted_id), "witness": witness},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

