from __future__ import annotations

from typing import Any, Dict

from datetime import datetime

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.recognition_pair import RecognitionPair
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RecognitionActHandler(ActHandler):
    """Per-act handler for ``recognition``.

    Runtime reflection of the *Recognition* act:
    the composition `(Void SelfNaming)` yielding a two-place recognition.

    Optionally, callers may also attach concrete ``left``/``right`` payloads
    or IDs that instantiate the two positions.

    Inputs (all optional):
      - left_id, right_id: identifiers of existing recognitions/points
      - left, right: inline payloads describing the two positions
    """

    acts = ["recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        left_id = context.get_input("left_id")
        right_id = context.get_input("right_id")
        left = context.get_input("left")
        right = context.get_input("right")

        left_ref = None
        if isinstance(left, dict) and "id" in left:
            left_ref = {
                "id": str(left["id"]),
                "acts": left.get("acts"),
            }
        right_ref = None
        if isinstance(right, dict) and "id" in right:
            right_ref = {
                "id": str(right["id"]),
                "acts": right.get("acts"),
            }

        payload = RecognitionPair(
            left_ref=left_ref,
            right_ref=right_ref,
            left=left if isinstance(left, dict) else None,
            right=right if isinstance(right, dict) else None,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="void", children=[]),
                ActTreeNode(act="self-naming", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        recognition: Dict[str, Any] = fibre.model_dump(mode="json")
        # Preserve the original surface shape expected by callers.
        recognition["type"] = "context"
        recognition["title"] = "Recognition (Void, SelfNaming)"
        recognition["act"] = act
        recognition["arity"] = 2
        recognition["left_id"] = left_id
        recognition["right_id"] = right_id
        recognition["left"] = left
        recognition["right"] = right
        recognition["recognized_at"] = datetime.utcnow().isoformat()
        recognition["trace_id"] = str(context.trace_id)

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "recognition_id": str(persisted_id),
                "recognition": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
