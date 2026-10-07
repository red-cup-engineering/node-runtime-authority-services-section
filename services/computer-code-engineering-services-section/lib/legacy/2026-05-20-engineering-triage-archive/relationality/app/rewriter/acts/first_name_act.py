from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class FirstNameHandler(ActHandler):
    """Per-act handler for ``first-name``.

    Runtime reflection of the *First Name* act: the trace `(Void Nothing)`,
    taking Void as witness and focusing it on Nothing.

    Inputs: none required.
    """

    acts = ["first-name"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "void"},
            {"act": "nothing"},
        ]

        recognition: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "FirstName (Void, Nothing)",
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
                "first_name": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
