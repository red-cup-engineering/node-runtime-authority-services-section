from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class BinderTransportHandler(ActHandler):
    """Per-act handler for ``binder-transport``."""

    acts = ["binder-transport"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        binder = context.get_input("binder")
        destination = context.get_input("destination")

        if not binder:
            return HandlerResult.fail("Missing required input: binder")

        transport = {
            "id": str(uuid4()),
            "type": "binder_transport",
            "act": act,
            "binder_id": binder.get("id"),
            "destination": destination,
            "transported_at": now,
        }

        return HandlerResult.ok(
            outputs={
                "transport": transport,
                "transported_binder": {**binder, "destination": destination},
            },
            metadata={"act": act},
        )

