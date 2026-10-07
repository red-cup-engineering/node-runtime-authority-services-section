from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.bind_trace import BindTracePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class BindTraceHandler(ActHandler):
    """Per-act handler for ``bind-trace``.

    Runtime reflection of *Bind Trace*: the composition `(FirstName HeadTrace)`,
    naming the head of the trace.
    """

    acts = ["bind-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace: Dict[str, Any] | None = context.get_input("trace")
        if not trace:
            return HandlerResult.fail("Missing required input: trace")

        now = datetime.utcnow().isoformat()

        binding_name = context.get_input("name")
        binding_value = context.get_input("value")

        if not binding_name:
            return HandlerResult.fail("Missing required input: name")

        bindings = dict(trace.get("bindings", {}))
        binding_record = {
            "value": binding_value,
            "bound_at": now,
            "witness": str(uuid4()),
        }
        bindings[binding_name] = binding_record

        bound_trace = dict(trace)
        bound_trace["bindings"] = bindings

        payload = BindTracePayload(
            trace_id=str(trace.get("id", "")),
            name=binding_name,
            binding=binding_record,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.TRACE,
            acts=[act],
            tree=[
                ActTreeNode(act="first-name", children=[]),
                ActTreeNode(act="head-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        return HandlerResult.ok(
            outputs={
                "trace": bound_trace,
                "binding": binding_record,
            },
            metadata={"act": act, "binding_name": binding_name},
        )
