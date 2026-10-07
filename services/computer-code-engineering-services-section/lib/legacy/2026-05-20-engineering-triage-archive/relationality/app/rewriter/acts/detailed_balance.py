from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class DetailedBalanceHandler(ActHandler):
    """Per-act handler for ``detailed-balance``.

    Checks the detailed balance condition for a Markov kernel and
    stationary distribution: π_i K_{ij} ≈ π_j K_{ji}.

    Inputs:
      - stationary_distribution: dict[str, float] (required)
      - transition_law: dict[str, dict[str, float]] (required)
      - tolerance: float (optional, default 1e-6)
    """

    acts = ["detailed-balance"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        pi: Dict[str, Any] = context.get_input("stationary_distribution", {})
        K: Dict[str, Any] = context.get_input("transition_law", {})
        tolerance = float(context.get_input("tolerance", 1e-6))

        if not pi:
            return HandlerResult.fail("Missing required input: stationary_distribution")
        if not K:
            return HandlerResult.fail("Missing required input: transition_law")

        states = sorted(set(K.keys()) | {s for row in K.values() for s in row.keys()})
        if not states:
            return HandlerResult.fail("Transition law has no states")

        def P(i: str, j: str) -> float:
            row = K.get(i, {})
            val = row.get(j, 0.0)
            return float(val)

        residuals: Dict[str, Dict[str, float]] = {}
        max_residual = 0.0
        for i in states:
            for j in states:
                pij = float(pi.get(i, 0.0)) * P(i, j)
                pji = float(pi.get(j, 0.0)) * P(j, i)
                r = abs(pij - pji)
                if r > 0.0:
                    residuals.setdefault(i, {})[j] = r
                    max_residual = max(max_residual, r)

        balanced = max_residual <= tolerance

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        db_recognition = {
            "id": str(uuid4()),
            "type": "detailed_balance",
            "title": "Detailed balance diagnostics",
            "act": act,
            "acts": [act],
            "tolerance": tolerance,
            "max_residual": max_residual,
            "balanced": balanced,
            "residuals": residuals,
            "evaluated_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(db_recognition)

        return HandlerResult.ok(
            outputs={
                "detailed_balance": db_recognition,
                "balanced": balanced,
                "max_residual": max_residual,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "balanced": balanced},
        )

