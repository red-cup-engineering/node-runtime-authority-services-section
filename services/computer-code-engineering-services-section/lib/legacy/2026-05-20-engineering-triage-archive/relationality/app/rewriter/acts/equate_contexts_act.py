from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.equate_contexts import EquateContextsPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class EquateContextsHandler(ActHandler):
    """Per-act handler for ``equate-contexts``.

    Runtime reflection of *Equate Contexts*: the composition
    `(RecognizeContext Normalization)` recording contextual
    indistinguishability of normalized terms.

    Inputs (all optional):
      - left: any – left normalized term/observation
      - right: any – right normalized term/observation
    """

    acts = ["equate-contexts"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        left: Any = context.get_input("left")
        right: Any = context.get_input("right")

        payload = EquateContextsPayload(left=left, right=right)

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="recognize-context", children=[]),
                ActTreeNode(act="normalization", children=[]),
            ],
            payload=payload.model_dump(),
        )

        record: Dict[str, Any] = fibre.model_dump(mode="json")
        record["id"] = str(uuid4())
        record["type"] = "context"
        record["title"] = "Equate contexts (RecognizeContext, Normalization)"
        record["act"] = act
        record["arity"] = 2
        record["left"] = left
        record["right"] = right
        record["recorded_at"] = datetime.utcnow().isoformat()
        record["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(record)

        return HandlerResult.ok(
            outputs={
                "equate_contexts": record,
                "equivalence_id": str(persisted_id),
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

