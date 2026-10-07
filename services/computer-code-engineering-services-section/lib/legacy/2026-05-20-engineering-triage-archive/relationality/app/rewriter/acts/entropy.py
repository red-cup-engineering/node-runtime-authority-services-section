from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.rewriter.measurement_algebra import compute_entropy


class EntropyHandler(ActHandler):
    """Handler for the ``entropy`` act.

    Implements entropy computation over a distribution in the
    measurement algebra.
    """

    acts = ["entropy"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        distribution = context.get_input("distribution", {})
        entropy_type = context.get_input("entropy_type", "shannon")

        value = compute_entropy(distribution, entropy_type)

        entropy_recognition = {
            "id": str(uuid4()),
            "type": "entropy",
            "act": act,
            "acts": [act],
            "distribution": distribution,
            "entropy_type": entropy_type,
            "value": value,
            "computed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(entropy_recognition)

        return HandlerResult.ok(
            outputs={
                "entropy": entropy_recognition,
                "entropy_id": entropy_recognition["id"],
                "value": value,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "entropy_type": entropy_type},
        )

