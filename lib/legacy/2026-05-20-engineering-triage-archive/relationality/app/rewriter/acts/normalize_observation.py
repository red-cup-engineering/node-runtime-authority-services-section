from __future__ import annotations

from datetime import datetime

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class NormalizeObservationHandler(ActHandler):
    """Per-act handler for ``normalize-observation``."""

    acts = ["normalize-observation"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        observation = context.get_input("observation")

        if observation is None:
            return HandlerResult.fail("Missing required input: observation")

        normalized = dict(observation)

        if "normalized_at" not in normalized:
            normalized["normalized_at"] = datetime.utcnow().isoformat()

        if "type" not in normalized:
            normalized["type"] = "observation"

        if "trace_id" not in normalized:
            normalized["trace_id"] = str(context.trace_id)

        if "metadata" not in normalized:
            normalized["metadata"] = {}

        normalized["metadata"]["normalization_act"] = act

        return HandlerResult.ok(
            outputs={"normalized": normalized},
            metadata={"act": act},
        )

