from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ReachLimitHandler(ActHandler):
    """Per-act handler for ``reach-limit``."""

    acts = ["reach-limit"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        reach_data = context.get_input("reach_data", [])

        limit = {
            "id": str(uuid4()),
            "type": "reach_limit",
            "act": act,
            "data_points": len(reach_data),
            "limit_value": None,
            "computed_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "limit": limit,
            },
            metadata={"act": act},
        )

