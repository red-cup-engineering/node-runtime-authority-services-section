from __future__ import annotations

from datetime import datetime

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class NormalizeStronglyHandler(ActHandler):
    """Per-act handler for ``normalize-strongly``.

    Applies strong normalization to an observation (same structural
    effect as ``normalize-observation`` for now, with a different mark).
    """

    acts = ["normalize-strongly"]

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
        normalized["metadata"]["strong_normalization"] = True

        return HandlerResult.ok(
            outputs={"normalized": normalized},
            metadata={"act": act},
        )

