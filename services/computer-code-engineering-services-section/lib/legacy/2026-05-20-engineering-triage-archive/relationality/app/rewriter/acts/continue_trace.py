from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ContinueTraceHandler(ActHandler):
    """Per-act handler for ``continue-trace``."""

    acts = ["continue-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        current_trace = context.get_input("trace")
        continuation_data = context.get_input("continuation_data", {})

        if not current_trace:
            return HandlerResult.fail("Missing required input: trace")

        continuation = {
            "id": str(uuid4()),
            "type": "continuation",
            "parent_trace_id": current_trace.get("id"),
            "continued_from_position": current_trace.get("current_position", 0),
            "continuation_data": continuation_data,
            "continued_at": now,
        }

        continued_trace = dict(current_trace)
        continued_trace["continued_at"] = now
        continued_trace["status"] = "continued"

        return HandlerResult.ok(
            outputs={
                "trace": continued_trace,
                "continuation": continuation,
            },
            metadata={"act": act},
        )

