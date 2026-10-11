from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.head_tail_trace import HeadTracePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class HeadTraceHandler(ActHandler):
    """Per-act handler for ``head-trace``.

    Runtime reflection of *Head Trace*: `(LeadEntry CompleteTrace)`.
    """

    acts = ["head-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace: Dict[str, Any] | None = context.get_input("trace")
        if not trace:
            return HandlerResult.fail("Missing required input: trace")

        now = datetime.utcnow().isoformat()
        steps: List[Dict[str, Any]] = trace.get("steps", [])
        count = context.get_input("count", 1)

        head_steps = steps[:count]
        head = {
            "id": str(uuid4()),
            "type": "trace_head",
            "source_trace_id": trace.get("id"),
            "head_count": count,
            "steps": head_steps,
            "extracted_at": now,
        }

        payload = HeadTracePayload(
            trace_id=str(trace.get("id", "")),
            count=len(head_steps),
            steps=head_steps,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.TRACE,
            acts=[act],
            tree=[
                ActTreeNode(act="lead-entry", children=[]),
                ActTreeNode(act="complete-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        return HandlerResult.ok(
            outputs={
                "head": head,
                "steps": head_steps,
                "count": len(head_steps),
            },
            metadata={"act": act},
        )
