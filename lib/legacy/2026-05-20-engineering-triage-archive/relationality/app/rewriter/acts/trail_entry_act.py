from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.entry_pair import EntryPairPayload
from app.schemas.fibers.payloads.lead_trail_entry import LeadTrailEntryPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class TrailEntryHandler(ActHandler):
    """Per-act handler for ``trail-entry``.

    Given an entry and (optionally) a lead entry, records the trailing
    orientation by focusing on the complementary position. At the act
    level this reflects the composition `(Entry LeadEntry)`.

    Inputs:
      - entry: dict (required) – entry record with ``left`` and ``right``.
    """

    acts = ["trail-entry"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        entry: Dict[str, Any] | None = context.get_input("entry")
        if not entry:
            return HandlerResult.fail("Missing required input: entry")

        left = entry.get("left")
        right = entry.get("right")
        if left is None or right is None:
            return HandlerResult.fail("Entry must contain 'left' and 'right'")

        entry_pair = EntryPairPayload(
            left_recognition=entry.get("left_recognition"),
            right_recognition=entry.get("right_recognition"),
            left=left if isinstance(left, dict) else None,
            right=right if isinstance(right, dict) else None,
        )

        payload = LeadTrailEntryPayload(
            entry=entry_pair,
            leader_position="left",
            trailing_position="right",
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="entry", children=[]),
                ActTreeNode(act="lead-entry", children=[]),
            ],
            payload=payload.model_dump(),
        )

        trail_entry = fibre.model_dump(mode="json")
        trail_entry["type"] = "context"
        trail_entry["title"] = "Trail entry (Entry, LeadEntry)"
        trail_entry["act"] = act
        trail_entry["arity"] = 2
        trail_entry["entry"] = entry
        trail_entry["leader"] = left
        trail_entry["trailing"] = right
        trail_entry["oriented_at"] = datetime.utcnow().isoformat()
        trail_entry["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(trail_entry)

        return HandlerResult.ok(
            outputs={
                "trail_entry": trail_entry,
                "leader": left,
                "trailing": right,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
