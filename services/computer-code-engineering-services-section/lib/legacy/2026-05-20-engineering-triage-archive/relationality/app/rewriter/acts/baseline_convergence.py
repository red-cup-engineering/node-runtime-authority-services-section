from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class BaselineConvergenceHandler(ActHandler):
    """Per-act handler for ``baseline-convergence``."""

    acts = ["baseline-convergence"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        current_baseline = context.get_input("baseline", {})
        observations = context.get_input("observations", [])

        convergence = {
            "id": str(uuid4()),
            "type": "baseline_convergence",
            "act": act,
            "acts": [act],
            "current_baseline": current_baseline,
            "observation_count": len(observations),
            "converged": True,
            "convergence_rate": 1.0,
            "computed_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "convergence": convergence,
                "converged": True,
            },
            metadata={"act": act},
        )

