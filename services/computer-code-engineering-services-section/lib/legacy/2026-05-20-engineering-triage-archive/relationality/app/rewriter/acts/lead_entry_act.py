from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.entry_pair import EntryPairPayload
from app.schemas.fibers.payloads.lead_trail_entry import LeadTrailEntryPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class LeadEntryHandler(ActHandler):
    """Per-act handler for ``lead-entry``.

    Selects a leading orientation for an entry: marks the left position as
    leader and records the oriented pair. At the act level this reflects
    the composition `(Entry Recognition)`.

    Inputs:
      - entry: dict (required) – entry record with at least ``left`` and ``right``.
    """

    acts = ["lead-entry"]

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

        entry_payload = LeadTrailEntryPayload(
            entry=entry_pair,
            leader_position="left",
            trailing_position="right",
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="entry", children=[]),
                ActTreeNode(act="recognition", children=[]),
            ],
            payload=entry_payload.model_dump(),
        )

        lead_entry = fibre.model_dump(mode="json")
        lead_entry["type"] = "context"
        lead_entry["title"] = "Lead entry (Entry, Recognition)"
        lead_entry["act"] = act
        lead_entry["arity"] = 2
        lead_entry["entry"] = entry
        lead_entry["leader"] = left
        lead_entry["trailing"] = right
        lead_entry["oriented_at"] = datetime.utcnow().isoformat()
        lead_entry["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(lead_entry)

        return HandlerResult.ok(
            outputs={
                "lead_entry": lead_entry,
                "leader": left,
                "trailing": right,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
