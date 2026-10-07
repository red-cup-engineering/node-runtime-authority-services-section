from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ShapeRecognitionHandler(ActHandler):
    """Per-act handler for ``shape-recognition``.

    Records that an implication respects an ordering, i.e. the internal
    "shape" of recognitions is compatible with the order.

    Inputs:
      - implication: any (required) – payload from imply-recognition
      - order: any (required) – payload from order-recognition
    """

    acts = ["shape-recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        implication = context.get_input("implication")
        order = context.get_input("order")

        if implication is None or order is None:
            return HandlerResult.fail("Missing required inputs: implication, order")

        now = datetime.utcnow().isoformat()

        shape: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Shape recognition",
            "act": act,
            "acts": [act],
            "implication": implication,
            "order": order,
            "recorded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(shape)

        return HandlerResult.ok(
            outputs={"shape_recognition": shape},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

