from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ModalityWitnessHandler(ActHandler):
    """Per-act handler for ``modality-witness``."""

    acts = ["modality-witness"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        modality = context.get_input("modality")
        witness_data = context.get_input("witness_data", {})

        if not modality:
            return HandlerResult.fail("Missing required input: modality")

        witness = {
            "id": str(uuid4()),
            "type": "modality_witness",
            "act": act,
            "acts": [act],
            "modality_id": modality.get("id"),
            "modality_type": modality.get("modality"),
            "witness_data": witness_data,
            "witnessed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(witness)

        return HandlerResult.ok(
            outputs={
                "witness": witness,
                "witness_id": witness["id"],
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

