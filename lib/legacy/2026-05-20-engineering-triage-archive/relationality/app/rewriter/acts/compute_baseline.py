from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ComputeBaselineHandler(ActHandler):
    """Per-act handler for ``compute-baseline``."""

    acts = ["compute-baseline"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        data = context.get_input("data", [])
        baseline_type = context.get_input("baseline_type", "mean")

        baseline = {
            "id": str(uuid4()),
            "type": "computed_baseline",
            "act": act,
            "data_points": len(data),
            "baseline_type": baseline_type,
            "value": None,
            "computed_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "baseline": baseline,
                "baseline_id": baseline["id"],
            },
            metadata={"act": act, "baseline_type": baseline_type},
        )

