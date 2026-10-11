from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.ground_cap_recognition import GroundRecognitionPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class GroundRecognitionHandler(ActHandler):
    """Per-act handler for ``ground-recognition``.

    Records the minimal / bottom recognition, representing absence.
    At the act level this reflects the composition
    `(Recognition Nothing)`.
    """

    acts = ["ground-recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        payload = GroundRecognitionPayload()

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="recognition", children=[]),
                ActTreeNode(act="nothing", children=[]),
            ],
            payload=payload.model_dump(),
        )

        recognition: Dict[str, Any] = fibre.model_dump(mode="json")
        recognition["type"] = "context"
        recognition["title"] = "Ground recognition (⊥)"
        recognition["act"] = act
        recognition["arity"] = 2
        recognition["kind"] = "ground"
        recognition["content"] = None
        recognition["grounded_at"] = datetime.utcnow().isoformat()
        recognition["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "recognition_id": str(persisted_id),
                "ground_recognition": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
