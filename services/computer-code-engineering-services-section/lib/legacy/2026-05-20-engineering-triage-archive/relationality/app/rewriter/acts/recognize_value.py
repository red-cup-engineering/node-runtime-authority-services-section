from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.recognize_value import RecognizeValuePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RecognizeValueHandler(ActHandler):
    """Per-act handler for ``recognize-value``.

    Runtime reflection of *Recognize Value*: the composition
    `(TailTrace SeedValue)`.
    """

    acts = ["recognize-value"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        value = context.get_input("value")
        observation_id = context.get_input("observation_id")

        if value is None and observation_id is None:
            return HandlerResult.fail("Missing required input: value or observation_id")

        recognition_id = uuid4()
        recognition: Dict[str, Any] = {
            "id": str(recognition_id),
            "type": "judgement",
            "title": "Recognition (value)",
            "act": act,
            "acts": [act],
            "value": value,
            "source_observation": observation_id,
            "recognized_at": datetime.utcnow().isoformat(),
            "trace_id": str(context.trace_id),
        }

        payload = RecognizeValuePayload(
            observation_id=str(observation_id) if observation_id is not None else None,
            value=value,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.JUDGEMENT,
            acts=[act],
            tree=[
                ActTreeNode(act="tail-trace", children=[]),
                ActTreeNode(act="seed-value", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={"recognition_id": str(persisted_id), "recognition": recognition},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
