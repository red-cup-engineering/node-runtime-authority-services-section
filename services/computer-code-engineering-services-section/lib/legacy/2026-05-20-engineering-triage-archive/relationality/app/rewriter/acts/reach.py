from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ReachHandler(ActHandler):
    """Per-act handler for ``reach``."""

    acts = ["reach"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        target = context.get_input("target")
        from_context = context.get_input("from_context")

        if target is None:
            return HandlerResult.fail("Missing required input: target")

        reach_result = {
            "id": str(uuid4()),
            "type": "reach",
            "act": act,
            "target": target,
            "from_context": from_context,
            "reachable": True,
            "path_length": 0,
            "computed_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "reach": reach_result,
                "reachable": True,
            },
            metadata={"act": act},
        )

