from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RelationlessnessHandler(ActHandler):
    """Per-act handler for ``relationlessness``.

    Records the canonical empty trace as a recognition. This is the
    runtime reflection of the act *Relationlessness*: the unique
    empty tree `()` with no prior recognitions.
    """

    acts = ["relationlessness"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        recognition = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Relationlessness (empty trace)",
            "act": act,
            "acts": [act],
            "tree": [],
            "arity": 0,
            "recorded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "recognition_id": str(persisted_id),
                "relationlessness": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
