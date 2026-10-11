from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RetraceContextHandler(ActHandler):
    """Per-act handler for ``retrace-context``."""

    acts = ["retrace-context"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        target_context = context.get_input("context")
        trace_to_replay = context.get_input("trace")

        if not target_context:
            return HandlerResult.fail("Missing required input: context")

        retrace_id = str(uuid4())
        retrace_record = {
            "id": retrace_id,
            "type": "retrace",
            "context_id": target_context.get("id"),
            "trace_id": trace_to_replay.get("id") if trace_to_replay else None,
            "retraced_at": now,
            "steps_considered": len(trace_to_replay.get("steps", []))
            if trace_to_replay
            else 0,
        }

        retraced_context = dict(target_context)
        retraced_context["retrace_id"] = retrace_id
        retraced_context["retraced_at"] = now

        return HandlerResult.ok(
            outputs={
                "context": retraced_context,
                "retrace": retrace_record,
            },
            metadata={"act": act},
        )

