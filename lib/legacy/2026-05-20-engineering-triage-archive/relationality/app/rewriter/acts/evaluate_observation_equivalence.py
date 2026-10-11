from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class EvaluateObservationEquivalenceHandler(ActHandler):
    """Per-act handler for ``evaluate-observation-equivalence``.

    Uses established recognitions to evaluate whether flowed observation
    pairs remain equivalent under the current recognitions.

    Inputs:
      - equivalence: dict (required)
        Flow observation equivalence recognition produced by
        ``flow-observation-equivalence``.
      - left_recognition: dict (optional) – recognition for left observation
      - right_recognition: dict (optional) – recognition for right observation
    """

    acts = ["evaluate-observation-equivalence"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        equivalence = context.get_input("equivalence")
        if equivalence is None or not isinstance(equivalence, dict):
            return HandlerResult.fail("Missing required input: equivalence")

        left_rec = context.get_input("left_recognition") or {}
        right_rec = context.get_input("right_recognition") or {}

        left_val = left_rec.get("value")
        right_val = right_rec.get("value")

        equal = left_val == right_val

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        eval_recognition = {
            "id": str(uuid4()),
            "type": "observation_equivalence_evaluation",
            "title": "Evaluation (observation equivalence)",
            "act": act,
            "acts": [act],
            "equivalence": equivalence,
            "left_recognition": left_rec,
            "right_recognition": right_rec,
            "left_value": left_val,
            "right_value": right_val,
            "equivalent": equal,
            "evaluated_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(eval_recognition)

        return HandlerResult.ok(
            outputs={
                "evaluation": eval_recognition,
                "equivalent": equal,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "equivalent": equal},
        )

