from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class NotRelateHandler(ActHandler):
    """Per-act handler for ``not-relate``.

    Runtime reflection of the *Not Relate* act: the trace `(Reflex Relate)`,
    with Reflex witnessing Relate.

    Inputs: none required.
    """

    acts = ["not-relate"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "reflex"},
            {"act": "relate"},
        ]

        recognition: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "NotRelate (Reflex, Relate)",
            "act": act,
            "acts": [act],
            "tree": tree,
            "arity": 2,
            "recorded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "recognition_id": str(persisted_id),
                "not_relate": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
