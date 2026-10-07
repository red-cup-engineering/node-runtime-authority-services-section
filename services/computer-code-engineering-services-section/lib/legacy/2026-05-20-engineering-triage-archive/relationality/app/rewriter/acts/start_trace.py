from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class StartTraceHandler(ActHandler):
    """Per-act handler for ``start-trace``."""

    acts = ["start-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        parent_trace = context.get_input("parent_trace")
        initial_data = context.get_input("initial_data", {})

        new_trace = {
            "id": str(uuid4()),
            "type": "trace",
            "act": act,
            "acts": [act],
            "parent_trace": parent_trace,
            "root_trace_id": trace_id,
            "started_at": now,
            "steps": [],
            "current_position": 0,
            "status": "active",
            "initial_data": initial_data,
        }

        persisted_id = await context.persist_recognition(new_trace)

        return HandlerResult.ok(
            outputs={
                "trace": new_trace,
                "trace_id": new_trace["id"],
                "position": 0,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

