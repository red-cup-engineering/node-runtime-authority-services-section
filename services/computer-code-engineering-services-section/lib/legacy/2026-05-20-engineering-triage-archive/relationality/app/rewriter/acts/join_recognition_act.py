from __future__ import annotations

from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.join_witness import JoinWitness
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class JoinRecognitionHandler(ActHandler):
    """Per-act handler for ``join-recognition``.

    Records the join (least upper bound) of two recognitions by
    aggregating their act footprints.

    Inputs:
      - left: dict (required) – recognition-like payload
      - right: dict (required) – recognition-like payload
    """

    acts = ["join-recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        left = context.get_input("left")
        right = context.get_input("right")

        if left is None or right is None:
            return HandlerResult.fail("Missing required inputs: left, right")

        if not isinstance(left, dict) or not isinstance(right, dict):
            return HandlerResult.fail("left and right must be dict payloads")

        left_acts = set(left.get("acts", []))
        right_acts = set(right.get("acts", []))
        union_acts = sorted(left_acts | right_acts)

        payload = JoinWitness(
            left_id=str(left.get("id", "")),
            right_id=str(right.get("id", "")),
            union_acts=union_acts,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[ActTreeNode(act=act, children=[])],
            payload=payload.model_dump(),
        )
        # Use JSON mode so UUIDs are rendered as strings for persistence.
        join: Dict[str, Any] = fibre.model_dump(mode="json")
        join["act"] = act

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(join)

        return HandlerResult.ok(
            outputs={
                "join": join,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
