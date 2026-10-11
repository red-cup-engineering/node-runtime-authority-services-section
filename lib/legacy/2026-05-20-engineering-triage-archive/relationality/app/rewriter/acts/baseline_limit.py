from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class BaselineLimitHandler(ActHandler):
    """Per-act handler for ``baseline-limit``."""

    acts = ["baseline-limit"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        baseline = context.get_input("baseline", {})
        limit_type = context.get_input("limit_type", "tail")

        limit = {
            "id": str(uuid4()),
            "type": "baseline_limit",
            "act": act,
            "acts": [act],
            "baseline": baseline,
            "limit_type": limit_type,
            "limit_value": None,
            "computed_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "limit": limit,
                "limit_id": limit["id"],
            },
            metadata={"act": act, "limit_type": limit_type},
        )

