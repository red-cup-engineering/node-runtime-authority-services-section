from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.renew_context import RenewContextPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RenewContextHandler(ActHandler):
    """Per-act handler for ``renew-context``.

    Runtime reflection of *Renew Context*: the composition
    `(ExtendFirstContext ContextualizeTrace)`, extending an initial
    seeded context and reattaching it to a contextualized trace.

    Inputs:
      - context: dict (required) – seeded or previously extended context
      - trace: dict (required) – base trace object
      - name: str (required) – assignment name
      - value: any (optional) – value to assign
      - result: any (optional) – final result to attach to the trace
      - bindings: dict (optional) – additional bindings for this renewal
    """

    acts = ["renew-context"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        seeded: Dict[str, Any] | None = context.get_input("context")
        trace: Dict[str, Any] | None = context.get_input("trace")
        name = context.get_input("name")
        value = context.get_input("value")
        result_payload = context.get_input("result")
        extra_bindings: Dict[str, Any] = context.get_input("bindings", {}) or {}

        if not seeded:
            return HandlerResult.fail("Missing required input: context")
        if not trace:
            return HandlerResult.fail("Missing required input: trace")
        if not name:
            return HandlerResult.fail("Missing required input: name")

        now = datetime.utcnow().isoformat()

        # First, extend the seeded context as in ExtendFirstContext.
        bindings = dict(seeded.get("bindings", {}))
        binding_record = {
            "value": value,
            "bound_at": now,
            "witness": str(uuid4()),
        }
        bindings[name] = binding_record
        bindings.update(extra_bindings)

        context_type = seeded.get("context_type", "evaluation")

        renewed_context: Dict[str, Any] = dict(seeded)
        renewed_context["id"] = str(uuid4())
        renewed_context["bindings"] = bindings
        renewed_context["context_type"] = context_type
        renewed_context["act"] = act
        renewed_context["acts"] = [act]
        renewed_context["renewed_at"] = now

        # Then, contextualize the trace as in ContextualizeTrace.
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

        renewed_context["anchored_trace_id"] = completed_trace.get("id")
        renewed_context["anchored_name"] = name

        payload = RenewContextPayload(
            context_id=str(seeded.get("id", "")),
            trace_id=str(completed_trace.get("id", "")),
            name=name,
            bindings=bindings,
            status=completed_trace["status"],
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="extend-first-context", children=[]),
                ActTreeNode(act="contextualize-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(renewed_context)

        return HandlerResult.ok(
            outputs={
                "context": renewed_context,
                "context_id": renewed_context["id"],
                "trace": completed_trace,
                "binding": binding_record,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

