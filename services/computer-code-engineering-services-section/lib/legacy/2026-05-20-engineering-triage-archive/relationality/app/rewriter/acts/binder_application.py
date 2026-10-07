from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class BinderApplicationHandler(ActHandler):
    """Per-act handler for ``binder-application``."""

    acts = ["binder-application"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        binder = context.get_input("binder")
        argument = context.get_input("argument")

        if not binder:
            return HandlerResult.fail("Missing required input: binder")

        application = {
            "id": str(uuid4()),
            "type": "binder_application",
            "act": act,
            "binder_id": binder.get("id"),
            "variable": binder.get("variable"),
            "argument": argument,
            "applied_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "application": application,
                "result": argument,
            },
            metadata={"act": act},
        )

