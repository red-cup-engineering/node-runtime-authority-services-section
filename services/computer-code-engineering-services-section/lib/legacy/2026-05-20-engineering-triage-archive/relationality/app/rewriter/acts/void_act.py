from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class VoidHandler(ActHandler):
    """Per-act handler for ``void``.

    Runtime reflection of the *Void* act: the trace `(Nothing Nothing)`,
    folding Nothing back on itself.

    Inputs: none required.
    """

    acts = ["void"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "nothing"},
            {"act": "nothing"},
        ]

        recognition: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Void (Nothing, Nothing)",
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
                "void": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
