from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class EmergeReflexHandler(ActHandler):
    """Per-act handler for ``emerge-reflex``.

    Runtime reflection of the *Emerge Reflex* act: the composition
    `(Relationlessness Articulate)` where the void witnesses articulation.

    Inputs: none required.
    """

    acts = ["emerge-reflex"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "relationlessness"},
            {"act": "articulate"},
        ]

        recognition = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Emerge Reflex (Relationlessness, Articulate)",
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
                "emerge_reflex": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
