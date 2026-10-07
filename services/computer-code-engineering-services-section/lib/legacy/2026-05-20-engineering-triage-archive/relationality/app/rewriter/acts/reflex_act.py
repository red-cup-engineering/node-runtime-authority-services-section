from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ReflexHandler(ActHandler):
    """Per-act handler for ``reflex``.

    Runtime reflection of the *Reflex* act: the trace `(EmergeReflex)`,
    treating EmergeReflex as a witness in its own right.

    Inputs: none required.
    """

    acts = ["reflex"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "emerge-reflex"},
        ]

        recognition: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Reflex (EmergeReflex)",
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
                "reflex": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
