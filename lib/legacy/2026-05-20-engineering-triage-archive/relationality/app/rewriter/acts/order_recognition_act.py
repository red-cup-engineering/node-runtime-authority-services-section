from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class OrderRecognitionHandler(ActHandler):
    """Per-act handler for ``order-recognition``.

    Records an ordering relation between two recognitions or positions.

    Inputs:
      - lower: any (required) – the recognition/position considered ≤ upper.
      - upper: any (required) – the recognition/position considered ≥ lower.
    """

    acts = ["order-recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        lower = context.get_input("lower")
        upper = context.get_input("upper")

        if lower is None:
            return HandlerResult.fail("Missing required input: lower")
        if upper is None:
            return HandlerResult.fail("Missing required input: upper")

        now = datetime.utcnow().isoformat()

        order: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Order recognition (≤)",
            "act": act,
            "acts": [act],
            "lower": lower,
            "upper": upper,
            "ordered_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(order)

        return HandlerResult.ok(
            outputs={
                "order": order,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

