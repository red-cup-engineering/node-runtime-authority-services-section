from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.seed_first_context import SeedFirstContextPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SeedFirstContextHandler(ActHandler):
    """Per-act handler for ``seed-first-context``.

    Runtime reflection of *Seed First Context*: the composition
    `(Nothing ContextualizeTrace)`, anchoring a named, contextualized
    trace back to the primordial witness *Nothing*.

    Inputs:
      - trace: dict (required) – base trace object
      - name: str (required) – assignment name for contextualization
      - value: any (optional) – value to assign
      - result: any (optional) – final result to attach to the trace
      - bindings: dict (optional) – initial context bindings
      - context_type: str (optional, default: 'evaluation')
    """

    acts = ["seed-first-context"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace: Dict[str, Any] | None = context.get_input("trace")
        name = context.get_input("name")
        value = context.get_input("value")
        result_payload = context.get_input("result")
        initial_bindings: Dict[str, Any] = context.get_input("bindings", {}) or {}
        context_type: str = context.get_input("context_type", "evaluation")

        if not trace:
            return HandlerResult.fail("Missing required input: trace")
        if not name:
            return HandlerResult.fail("Missing required input: name")

        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        # Contextualize the trace: assign then complete, mirroring
        # (AssignTrace CompleteTrace) from the ContextualizeTrace act.
        assignments = dict(trace.get("assignments", {}))
        assignments[name] = {
            "value": value,
            "assigned_at": now,
        }

        assigned_trace = dict(trace)
        assigned_trace["assignments"] = assignments

        completed_trace = dict(assigned_trace)
        completed_trace["status"] = "completed"
        completed_trace["completed_at"] = now
        if result_payload is not None:
            completed_trace["result"] = result_payload

        assignment_record = assignments[name]

        # Build the seeded context, anchoring it to the contextualized trace.
        context_id = str(uuid4())
        first_context: Dict[str, Any] = {
            "id": context_id,
            "type": "context",
            "context_type": context_type,
            "act": act,
            "acts": [act],
            "bindings": initial_bindings,
            "parent_context": None,
            "depth": 0,
            "anchored_trace_id": completed_trace.get("id"),
            "anchored_name": name,
            "trace_id": trace_id,
            "seeded_at": now,
        }

        payload = SeedFirstContextPayload(
            trace_id=str(completed_trace.get("id", "")),
            name=name,
            bindings=initial_bindings,
            context_type=context_type,
            status=completed_trace["status"],
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="nothing", children=[]),
                ActTreeNode(act="contextualize-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(first_context)

        return HandlerResult.ok(
            outputs={
                "context": first_context,
                "context_id": first_context["id"],
                "trace": completed_trace,
                "assignment": assignment_record,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

