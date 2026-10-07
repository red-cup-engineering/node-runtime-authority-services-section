from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class EvaluateJudgementHandler(ActHandler):
    """Per-act handler for ``evaluate-judgement``.

    Evaluates flowed judgements as stabilised values by extracting
    their recognised values and recording an evaluation summary.

    Inputs:
      - judgements: list[dict] or dict (required)
        Flowed judgement recognitions to evaluate.
    """

    acts = ["evaluate-judgement"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        judgements_in = context.get_input("judgements")
        if judgements_in is None:
            return HandlerResult.fail("Missing required input: judgements")

        if isinstance(judgements_in, dict):
            judgements: List[Dict[str, Any]] = [judgements_in]
        elif isinstance(judgements_in, list):
            judgements = [j for j in judgements_in if isinstance(j, dict)]
        else:
            return HandlerResult.fail("Input 'judgements' must be dict or list of dicts")

        values: List[Any] = []
        for j in judgements:
            if "value" in j:
                values.append(j["value"])

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        evaluation = {
            "id": str(uuid4()),
            "type": "judgement_evaluation",
            "title": "Evaluation (judgement)",
            "act": act,
            "acts": [act],
            "judgements": judgements,
            "values": values,
            "evaluated_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(evaluation)

        return HandlerResult.ok(
            outputs={
                "evaluation": evaluation,
                "values": values,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

