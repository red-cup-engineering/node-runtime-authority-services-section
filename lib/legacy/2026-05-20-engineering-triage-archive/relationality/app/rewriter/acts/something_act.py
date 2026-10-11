from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SomethingHandler(ActHandler):
    """Per-act handler for ``something``.

    Runtime reflection of the *Something* act: the trace `(Reflex Witness)`,
    pointing Reflex at the testimony itself.

    Inputs: none required.
    """

    acts = ["something"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "reflex"},
            {"act": "witness"},
        ]

        recognition: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Something (Reflex, Witness)",
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
                "something": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
