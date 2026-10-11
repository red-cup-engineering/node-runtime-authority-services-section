from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class BinderSeedHandler(ActHandler):
    """Per-act handler for ``binder-seed``."""

    acts = ["binder-seed"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        variable_name = context.get_input("variable")
        variable_type = context.get_input("type", "any")

        if not variable_name:
            return HandlerResult.fail("Missing required input: variable")

        binder = {
            "id": str(uuid4()),
            "type": "binder",
            "act": act,
            "acts": [act],
            "variable": variable_name,
            "variable_type": variable_type,
            "bound_value": None,
            "seeded_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(binder)

        return HandlerResult.ok(
            outputs={
                "binder": binder,
                "binder_id": binder["id"],
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "variable": variable_name},
        )

