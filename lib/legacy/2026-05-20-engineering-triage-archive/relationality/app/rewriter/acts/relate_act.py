from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RelateHandler(ActHandler):
    """Per-act handler for ``relate``.

    Runtime reflection of the *Relate* act: the trace `(Reflex)`,
    treating Reflex as the definition of Relate.

    Inputs: none required.
    """

    acts = ["relate"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "reflex"},
        ]

        recognition: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Relate (Reflex)",
            "act": act,
            "acts": [act],
            "tree": tree,
            "arity": 1,
            "recorded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "recognition_id": str(persisted_id),
                "relate": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
