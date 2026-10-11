from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SelfNamingHandler(ActHandler):
    """Per-act handler for ``self-naming``.

    Runtime reflection of the *Self Naming* act: the trace
    `(FirstName FirstName)`, self-application of the first name.

    Inputs: none required.
    """

    acts = ["self-naming"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "first-name"},
            {"act": "first-name"},
        ]

        recognition: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "SelfNaming (FirstName, FirstName)",
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
                "self_naming": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
