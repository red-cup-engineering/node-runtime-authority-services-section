from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.seed_value import SeedValuePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SeedValueHandler(ActHandler):
    """Per-act handler for ``seed-value``.

    Runtime reflection of *Seed Value*: `(HeadTrace Normalization)`.
    """

    acts = ["seed-value"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        payload_value = context.get_input("payload")
        if payload_value is None:
            return HandlerResult.fail("Missing required input: payload")

        observation_id = uuid4()
        observation: Dict[str, Any] = {
            "id": str(observation_id),
            "type": "observation",
            "title": "Seeded value",
            "act": act,
            "acts": [act],
            "payload": payload_value,
            "seeded_at": datetime.utcnow().isoformat(),
            "trace_id": str(context.trace_id),
        }

        payload = SeedValuePayload(payload=payload_value)

        fibre = RecognitionFiber(
            role=RecognitionRole.OBSERVATION,
            acts=[act],
            tree=[
                ActTreeNode(act="head-trace", children=[]),
                ActTreeNode(act="normalization", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(observation)

        return HandlerResult.ok(
            outputs={"observation_id": str(persisted_id), "observation": observation},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

