from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.assign_trace import AssignTracePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class AssignTraceHandler(ActHandler):
    """Per-act handler for ``assign-trace``.

    Runtime reflection of *Assign Trace*: the composition
    `(BindTrace TailTrace)`, extending a name across the trace tail.
    """

    acts = ["assign-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace: Dict[str, Any] | None = context.get_input("trace")
        name = context.get_input("name")
        value = context.get_input("value")

        if not trace:
            return HandlerResult.fail("Missing required input: trace")
        if not name:
            return HandlerResult.fail("Missing required input: name")

        now = datetime.utcnow().isoformat()

        assignments = dict(trace.get("assignments", {}))
        assignment_record = {
            "value": value,
            "assigned_at": now,
            "witness": str(uuid4()),
        }
        assignments[name] = assignment_record

        assigned_trace = dict(trace)
        assigned_trace["assignments"] = assignments

        payload = AssignTracePayload(
            trace_id=str(trace.get("id", "")),
            name=name,
            assignment=assignment_record,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.TRACE,
            acts=[act],
            tree=[
                ActTreeNode(act="bind-trace", children=[]),
                ActTreeNode(act="tail-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        return HandlerResult.ok(
            outputs={
                "trace": assigned_trace,
                "assignment": assignment_record,
            },
            metadata={"act": act, "name": name},
        )

