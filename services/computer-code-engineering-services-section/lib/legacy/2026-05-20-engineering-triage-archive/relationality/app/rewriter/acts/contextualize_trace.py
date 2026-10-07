from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.contextualized_trace import ContextualizedTracePayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ContextualizeTraceHandler(ActHandler):
    """Per-act handler for ``contextualize-trace``.

    Runtime reflection of *Contextualize Trace*: the composition
    `(AssignTrace CompleteTrace)`, coupling a named assignment with
    the completed trace it encloses.

    Inputs:
      - trace: dict (required) – base trace object
      - name: str (required) – assignment name
      - value: any (optional) – value to assign
      - result: any (optional) – final result to attach to the trace
    """

    acts = ["contextualize-trace"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace = context.get_input("trace")
        name = context.get_input("name")
        value = context.get_input("value")
        result_payload = context.get_input("result")

        if not trace:
            return HandlerResult.fail("Missing required input: trace")
        if not name:
            return HandlerResult.fail("Missing required input: name")

        now = datetime.utcnow().isoformat()

        # First, assign the named value into the trace, as in AssignTrace.
        assignments = dict(trace.get("assignments", {}))
        assignments[name] = {
            "value": value,
            "assigned_at": now,
        }

        assigned_trace = dict(trace)
        assigned_trace["assignments"] = assignments

        # Then, complete the trace, as in CompleteTrace.
        completed_trace = dict(assigned_trace)
        completed_trace["status"] = "completed"
        completed_trace["completed_at"] = now
        if result_payload is not None:
            completed_trace["result"] = result_payload

        assignment_record = assignments[name]

        payload = ContextualizedTracePayload(
            trace_id=str(completed_trace.get("id", "")),
            name=name,
            assignment=assignment_record,
            status=completed_trace["status"],
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.TRACE,
            acts=[act],
            tree=[
                ActTreeNode(act="assign-trace", children=[]),
                ActTreeNode(act="complete-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        contextualized: Dict[str, Any] = fibre.model_dump(mode="json")
        contextualized["type"] = "trace"
        contextualized["title"] = "Contextualized trace (AssignTrace, CompleteTrace)"
        contextualized["act"] = act
        contextualized["trace"] = completed_trace
        contextualized["name"] = name
        contextualized["value"] = value
        contextualized["result"] = result_payload
        contextualized["contextualized_at"] = now
        contextualized["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        # Persist a lightweight recognition so the traceability layer can
        # witness this contextualization.
        await context.persist_recognition(contextualized)

        return HandlerResult.ok(
            outputs={
                "trace": completed_trace,
                "contextualized_trace": contextualized,
            },
            recognitions_created=[],
            metadata={"act": act, "name": name},
        )

