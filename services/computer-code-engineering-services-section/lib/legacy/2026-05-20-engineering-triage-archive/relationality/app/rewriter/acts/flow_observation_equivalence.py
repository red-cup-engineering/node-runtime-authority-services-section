from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class FlowObservationEquivalenceHandler(ActHandler):
    """Per-act handler for ``flow-observation-equivalence``.

    Records that two observations remain equivalent after flowing
    through evaluation contexts. This is a bookkeeping act that
    builds an explicit equivalence record, to be used by the
    observable algebra and measurement stack.

    Inputs:
      - left_observation: dict (required)
      - right_observation: dict (required)
      - context: dict (optional)
    """

    acts = ["flow-observation-equivalence"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        left = context.get_input("left_observation")
        right = context.get_input("right_observation")
        if left is None or right is None:
            return HandlerResult.fail(
                "Missing required inputs: left_observation and right_observation"
            )

        eval_context = context.get_input("context")
        now = datetime.utcnow().isoformat()

        equivalence = {
            "id": str(uuid4()),
            "type": "observation_equivalence",
            "title": "Flow observation equivalence",
            "act": act,
            "acts": [act],
            "left_observation_id": left.get("id"),
            "right_observation_id": right.get("id"),
            "context": eval_context,
            "witnessed_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(equivalence)

        return HandlerResult.ok(
            outputs={
                "equivalence": equivalence,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

