from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.extend_context import ExtendContextPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ExtendContextHandler(ActHandler):
    """Per-act handler for ``extend-context``.

    Runtime reflection of *Extend Context*: the composition
    `(BindTrace RenewContext)`, attaching new bindings to a renewed
    context.
    """

    acts = ["extend-context"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        parent_context: Dict[str, Any] | None = context.get_input("context")
        extension_bindings: Dict[str, Any] = context.get_input("bindings", {}) or {}

        if not parent_context:
            return HandlerResult.fail("Missing required input: context")

        parent_bindings = parent_context.get("bindings", {})
        merged_bindings = {**parent_bindings, **extension_bindings}

        depth = parent_context.get("depth", 0) + 1
        context_type = parent_context.get("context_type", "evaluation")

        extended_context = {
            "id": str(uuid4()),
            "type": "context",
            "context_type": context_type,
            "act": act,
            "acts": [act],
            "bindings": merged_bindings,
            "parent_context": parent_context.get("id"),
            "depth": depth,
            "trace_id": trace_id,
            "extended_at": now,
        }

        payload = ExtendContextPayload(
            parent_context_id=str(parent_context.get("id", "")),
            bindings=merged_bindings,
            context_type=context_type,
            depth=depth,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="bind-trace", children=[]),
                ActTreeNode(act="renew-context", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(extended_context)

        return HandlerResult.ok(
            outputs={
                "context": extended_context,
                "context_id": extended_context["id"],
                "depth": extended_context["depth"],
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "depth": extended_context["depth"]},
        )
