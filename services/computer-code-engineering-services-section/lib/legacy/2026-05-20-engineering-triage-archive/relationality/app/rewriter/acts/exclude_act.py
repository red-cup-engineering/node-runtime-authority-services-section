from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ExcludeHandler(ActHandler):
    """Per-act handler for ``exclude``.

    Runtime reflection of the *Exclude* act:
    the composition `(Relationlessness Relationlessness)` expressing
    exclusion as the void witnessing itself.

    Inputs: none required.
    """

    acts = ["exclude"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "relationlessness"},
            {"act": "relationlessness"},
        ]

        recognition = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Exclude (Relationlessness, Relationlessness)",
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
                "exclude": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
