from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.witness import WitnessPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class WitnessActHandler(ActHandler):
    """Per-act handler for ``witness``.

    Runtime reflection of the *Witness* act: the trace `(NotRelate Relate)`,
    where NotRelate witnesses Relate.
    """

    acts = ["witness"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()

        tree: List[Dict[str, Any]] = [
            {"act": "not-relate"},
            {"act": "relate"},
        ]

        payload = WitnessPayload()

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="not-relate", children=[]),
                ActTreeNode(act="relate", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        recognition: Dict[str, Any] = {
            "id": str(fibre.id),
            "type": "context",
            "title": "Witness (NotRelate, Relate)",
            "act": act,
            "acts": [act],
            "tree": tree,
            "arity": 2,
            "recorded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "recognition_id": str(persisted_id),
                "witness": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
