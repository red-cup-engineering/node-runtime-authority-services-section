from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.complete_trace import CompleteTracePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class CompleteTraceHandler(ActHandler):
    """Per-act handler for ``complete-trace``.

    Runtime reflection of *Complete Trace*: `(StartTrace AdvanceTrace)`.

    This act marks a trace as completed and optionally records a
    final result payload.

    Inputs:
      - trace: dict (required) – the trace object to complete
      - result: any (optional) – final result to attach to the trace
    """

    acts = ["complete-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace: Dict[str, Any] | None = context.get_input("trace")
        if not trace:
            return HandlerResult.fail("Missing required input: trace")

        result_payload = context.get_input("result")
        now = datetime.utcnow().isoformat()

        completed_trace = dict(trace)
        completed_trace["status"] = "completed"
        completed_trace["completed_at"] = now
        if result_payload is not None:
            completed_trace["result"] = result_payload

        payload = CompleteTracePayload(
            trace_id=str(completed_trace.get("id", "")),
            status=completed_trace["status"],
            result=result_payload if isinstance(result_payload, dict) else None,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.TRACE,
            acts=[act],
            tree=[
                ActTreeNode(act="start-trace", children=[]),
                ActTreeNode(act="advance-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        # Preserve the lightweight completion recognition for traceability.
        completion_recognition = {
            "id": str(uuid4()),
            "type": "trace_completion",
            "act": act,
            "acts": [act],
            "trace_id": completed_trace.get("id"),
            "completed_at": now,
            "trace_status": completed_trace.get("status"),
        }

        persisted_id = await context.persist_recognition(completion_recognition)

        return HandlerResult.ok(
            outputs={
                "trace": completed_trace,
                "completion": completion_recognition,
                "completion_id": completion_recognition["id"],
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

