from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.witness_value import WitnessValuePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class WitnessValueHandler(ActHandler):
    """Per-act handler for ``witness-value``.

    Runtime reflection of *Witness Value*: `(RecognizeValue Normalization)`.
    """

    acts = ["witness-value"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        target_id = context.get_input("target_id")
        judgement_type = context.get_input("judgement_type", "observation")

        if target_id is None:
            return HandlerResult.fail("Missing required input: target_id")

        witness_id = uuid4()
        witness: Dict[str, Any] = {
            "id": str(witness_id),
            "type": "witness",
            "title": "Witness (value)",
            "act": act,
            "acts": [act],
            "target_id": target_id,
            "judgement_type": judgement_type,
            "witnessed_at": datetime.utcnow().isoformat(),
            "trace_id": str(context.trace_id),
        }

        payload = WitnessValuePayload(target_id=str(target_id))

        fibre = RecognitionFiber(
            role=RecognitionRole.WITNESS,
            acts=[act],
            tree=[
                ActTreeNode(act="recognize-value", children=[]),
                ActTreeNode(act="normalization", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(witness)

        return HandlerResult.ok(
            outputs={"witness_id": str(persisted_id), "witness": witness},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

