from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class MixingHandler(ActHandler):
    """Per-act handler for ``mixing``.

    Specialises profile mixing diagnostics to a distribution sequence,
    computing simple total-variation style distances to indicate
    whether the sequence has mixed.

    Inputs:
      - history: list[dict] (required)
          Sequence of distributions over the same state space, in the
          form produced by ``fixed-kernel`` (each entry is a mapping
          state -> probability).
      - threshold: float (optional, default 1e-3)
          Threshold on L1 distance to consider the sequence mixed.
    """

    acts = ["mixing"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        history: List[Dict[str, Any]] = context.get_input("history", [])
        if not history:
            return HandlerResult.fail("Missing required input: history")

        threshold = float(context.get_input("threshold", 1e-3))

        # Determine common state space from union of keys.
        states = sorted({s for dist in history for s in dist.keys()})
        if not states:
            return HandlerResult.fail("History distributions have no states")

        def l1(a: Dict[str, float], b: Dict[str, float]) -> float:
            return sum(abs(float(a.get(s, 0.0)) - float(b.get(s, 0.0))) for s in states)

        # Compute distances between first and last, and between consecutive steps.
        first = history[0]
        last = history[-1]
        distance_first_last = l1(first, last)

        consecutive_distances: List[float] = []
        for i in range(1, len(history)):
            consecutive_distances.append(l1(history[i - 1], history[i]))

        max_consecutive_distance: Optional[float] = (
            max(consecutive_distances) if consecutive_distances else None
        )

        mixed = distance_first_last < threshold

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        mixing_recognition = {
            "id": str(uuid4()),
            "type": "mixing_diagnostic",
            "title": "Mixing diagnostics",
            "act": act,
            "acts": [act],
            "distance_first_last": distance_first_last,
            "consecutive_distances": consecutive_distances,
            "max_consecutive_distance": max_consecutive_distance,
            "threshold": threshold,
            "mixed": mixed,
            "history_length": len(history),
            "evaluated_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(mixing_recognition)

        return HandlerResult.ok(
            outputs={
                "mixing": mixing_recognition,
                "mixed": mixed,
                "distance_first_last": distance_first_last,
                "max_consecutive_distance": max_consecutive_distance,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "mixed": mixed},
        )

