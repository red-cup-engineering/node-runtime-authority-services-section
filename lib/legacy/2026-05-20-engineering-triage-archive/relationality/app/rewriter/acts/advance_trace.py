from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class AdvanceTraceHandler(ActHandler):
    """Per-act handler for ``advance-trace``."""

    acts = ["advance-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        current_trace = context.get_input("trace")
        step_data = context.get_input("step_data", {})

        if not current_trace:
            return HandlerResult.fail("Missing required input: trace")

        position = current_trace.get("current_position", 0) + 1
        step = {
            "position": position,
            "data": step_data,
            "advanced_at": now,
            "witness": str(uuid4()),
        }

        steps = list(current_trace.get("steps", []))
        steps.append(step)

        advanced_trace = dict(current_trace)
        advanced_trace["steps"] = steps
        advanced_trace["current_position"] = position
        advanced_trace["last_advanced"] = now

        return HandlerResult.ok(
            outputs={
                "trace": advanced_trace,
                "step": step,
                "position": position,
            },
            metadata={"act": act, "position": position},
        )

