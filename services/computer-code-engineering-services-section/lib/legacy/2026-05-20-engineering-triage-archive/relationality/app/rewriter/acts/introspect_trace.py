from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class IntrospectTraceHandler(ActHandler):
    """Helper for inspecting traces.

    This is not a first-class act; it is a utility that may be called
    directly by internal tooling or interfaces.
    """

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace = context.get_input("trace")
        depth = context.get_input("depth", 1)

        if not trace:
            return HandlerResult.fail("Missing required input: trace")

        now = datetime.utcnow().isoformat()

        introspection = {
            "id": str(uuid4()),
            "type": "trace_introspection",
            "act": act,
            "trace_id": trace.get("id"),
            "depth": depth,
            "step_count": len(trace.get("steps", [])),
            "current_position": trace.get("current_position", 0),
            "status": trace.get("status", "unknown"),
            "introspected_at": now,
        }

        return HandlerResult.ok(
            outputs={
                "introspection": introspection,
                "step_count": introspection["step_count"],
            },
            metadata={"act": act, "depth": depth},
        )
