from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RestepTraceHandler(ActHandler):
    """Per-act handler for ``restep-trace``."""

    acts = ["restep-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace = context.get_input("trace")
        if not trace:
            return HandlerResult.fail("Missing required input: trace")

        now = datetime.utcnow().isoformat()
        from_position = context.get_input("from_position", 0)

        steps = trace.get("steps", [])
        restep_id = str(uuid4())

        restep_record = {
            "id": restep_id,
            "type": "restep",
            "trace_id": trace.get("id"),
            "from_position": from_position,
            "to_position": trace.get("current_position", 0),
            "steps_replayed": len(
                [s for s in steps if s.get("position", 0) >= from_position]
            ),
            "restepped_at": now,
        }

        restepped_trace = dict(trace)
        restepped_trace["restep_id"] = restep_id
        restepped_trace["restepped_at"] = now

        return HandlerResult.ok(
            outputs={
                "trace": restepped_trace,
                "restep": restep_record,
            },
            metadata={"act": act, "from_position": from_position},
        )

