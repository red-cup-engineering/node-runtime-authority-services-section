from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.entry_pair import EntryPairPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class EntryHandler(ActHandler):
    """Per-act handler for ``entry``.

    Runtime reflection of the *Entry* act:
    the composition `(Recognition Recognition)` recording a structured
    two-place entry.

    Optionally, callers may attach concrete ``left``/``right`` payloads
    or recognitions instantiating the positions.

    Inputs (all optional):
      - left_recognition: any – concrete left recognition
      - right_recognition: any – concrete right recognition
      - left: any – payload for left position
      - right: any – payload for right position
    """

    acts = ["entry"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        left_rec = context.get_input("left_recognition")
        right_rec = context.get_input("right_recognition")
        left = context.get_input("left")
        right = context.get_input("right")

        left_ref = None
        if isinstance(left_rec, dict) and "id" in left_rec:
            left_ref = {
                "id": str(left_rec["id"]),
                "acts": left_rec.get("acts"),
            }
        right_ref = None
        if isinstance(right_rec, dict) and "id" in right_rec:
            right_ref = {
                "id": str(right_rec["id"]),
                "acts": right_rec.get("acts"),
            }

        payload = EntryPairPayload(
            left_recognition=left_ref,
            right_recognition=right_ref,
            left=left if isinstance(left, dict) else None,
            right=right if isinstance(right, dict) else None,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="recognition", children=[]),
                ActTreeNode(act="recognition", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        entry = fibre.model_dump(mode="json")
        entry["type"] = "context"
        entry["title"] = "Entry (Recognition, Recognition)"
        entry["act"] = act
        entry["arity"] = 2
        entry["left_recognition"] = left_rec
        entry["right_recognition"] = right_rec
        entry["left"] = left
        entry["right"] = right
        entry["entered_at"] = datetime.utcnow().isoformat()
        entry["trace_id"] = str(context.trace_id)

        persisted_id = await context.persist_recognition(entry)

        return HandlerResult.ok(
            outputs={
                "entry": entry,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
