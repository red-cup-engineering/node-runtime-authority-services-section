from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.head_tail_trace import TailTracePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class TailTraceHandler(ActHandler):
    """Per-act handler for ``tail-trace``.

    Runtime reflection of *Tail Trace*: `(TrailEntry CompleteTrace)`.
    """

    acts = ["tail-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace: Dict[str, Any] | None = context.get_input("trace")
        if not trace:
            return HandlerResult.fail("Missing required input: trace")

        now = datetime.utcnow().isoformat()
        steps: List[Dict[str, Any]] = trace.get("steps", [])
        count = context.get_input("count", 1)

        tail_steps = steps[-count:] if count <= len(steps) else steps
        tail = {
            "id": str(uuid4()),
            "type": "trace_tail",
            "source_trace_id": trace.get("id"),
            "tail_count": count,
            "steps": tail_steps,
            "extracted_at": now,
        }

        payload = TailTracePayload(
            trace_id=str(trace.get("id", "")),
            count=len(tail_steps),
            steps=tail_steps,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.TRACE,
            acts=[act],
            tree=[
                ActTreeNode(act="trail-entry", children=[]),
                ActTreeNode(act="complete-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        return HandlerResult.ok(
            outputs={
                "tail": tail,
                "steps": tail_steps,
                "count": len(tail_steps),
            },
            metadata={"act": act},
        )
