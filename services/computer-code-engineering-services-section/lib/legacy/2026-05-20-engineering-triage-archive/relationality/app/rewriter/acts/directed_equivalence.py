from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class DirectedEquivalenceHandler(ActHandler):
    """Directed space helper (not a core act)."""

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        left = context.get_input("left")
        right = context.get_input("right")

        if left is None or right is None:
            return HandlerResult.fail("Missing required inputs: left, right")

        equivalence = {
            "id": str(uuid4()),
            "type": "directed_equivalence",
            "act": act,
            "left": left,
            "right": right,
            "equivalent": True,
            "established_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "equivalence": equivalence,
                "equivalence_id": equivalence["id"],
                "equivalent": True,
            },
            metadata={"act": act},
        )
