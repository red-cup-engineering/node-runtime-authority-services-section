from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ModalityTransportHandler(ActHandler):
    """Per-act handler for ``modality-transport``."""

    acts = ["modality-transport"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        source_modality = context.get_input("source")
        target_world = context.get_input("target_world")

        if not source_modality:
            return HandlerResult.fail("Missing required input: source")

        transported = {
            "id": str(uuid4()),
            "type": "transported_modality",
            "act": act,
            "source_modality_id": source_modality.get("id"),
            "source_world": source_modality.get("world"),
            "target_world": target_world,
            "transported_at": now,
        }

        return HandlerResult.ok(
            outputs={
                "transported": transported,
                "transport_id": transported["id"],
            },
            metadata={"act": act},
        )

