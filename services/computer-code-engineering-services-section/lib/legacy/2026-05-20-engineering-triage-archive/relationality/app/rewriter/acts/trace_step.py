from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class TraceStepHandler(ActHandler):
    """Per-act handler for ``trace-step``."""

    acts = ["trace-step"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        current_trace = context.get_input("trace")
        step_operation = context.get_input("operation")
        step_payload = context.get_input("payload", {})

        if not current_trace:
            return HandlerResult.fail("Missing required input: trace")

        position = current_trace.get("current_position", 0) + 1
        step = {
            "position": position,
            "operation": step_operation,
            "payload": step_payload,
            "stepped_at": now,
            "witness": str(uuid4()),
        }

        steps = list(current_trace.get("steps", []))
        steps.append(step)

        updated_trace = dict(current_trace)
        updated_trace["steps"] = steps
        updated_trace["current_position"] = position

        return HandlerResult.ok(
            outputs={
                "trace": updated_trace,
                "step": step,
                "position": position,
            },
            metadata={"act": act, "position": position},
        )

