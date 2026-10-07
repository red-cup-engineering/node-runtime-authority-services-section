from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class NothingHandler(ActHandler):
    """Per-act handler for ``nothing``.

    Runtime reflection of the *Nothing* act: the trace `(Witness Something)`,
    witnessing Something directly.

    Inputs: none required.
    """

    acts = ["nothing"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "witness"},
            {"act": "something"},
        ]

        recognition: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Nothing (Witness, Something)",
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
                "nothing": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
