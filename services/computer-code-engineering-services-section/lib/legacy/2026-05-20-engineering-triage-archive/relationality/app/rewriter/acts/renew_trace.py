from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RenewTraceHandler(ActHandler):
    """Per-act handler for ``renew-trace``."""

    acts = ["renew-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace = context.get_input("trace")
        if not trace:
            return HandlerResult.fail("Missing required input: trace")

        now = datetime.utcnow().isoformat()
        baseline = context.get_input("baseline", {})

        renewal_id = str(uuid4())
        renewed_trace = dict(trace)
        renewed_trace["renewal_id"] = renewal_id
        renewed_trace["renewed_at"] = now
        renewed_trace["baseline"] = baseline
        renewed_trace["status"] = "renewed"

        renewal_record = {
            "id": renewal_id,
            "type": "renewal",
            "trace_id": trace.get("id"),
            "baseline": baseline,
            "renewed_at": now,
            "position_at_renewal": trace.get("current_position", 0),
        }

        return HandlerResult.ok(
            outputs={
                "trace": renewed_trace,
                "renewal": renewal_record,
                "renewal_id": renewal_id,
            },
            metadata={"act": act},
        )

