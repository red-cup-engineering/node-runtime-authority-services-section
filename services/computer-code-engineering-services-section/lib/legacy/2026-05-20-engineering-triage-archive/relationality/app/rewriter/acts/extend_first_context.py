from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.extend_first_context import ExtendFirstContextPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ExtendFirstContextHandler(ActHandler):
    """Per-act handler for ``extend-first-context``.

    Runtime reflection of *Extend First Context*: the composition
    `(BindTrace SeedFirstContext)`, extending the initially seeded
    context with an additional binding while remaining at depth 0.

    Inputs:
      - context: dict (required) – seeded context to extend
      - name: str (required) – name of the new binding
      - value: any (optional) – value to bind
    """

    acts = ["extend-first-context"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        seeded: Dict[str, Any] | None = context.get_input("context")
        name = context.get_input("name")
        value = context.get_input("value")

        if not seeded:
            return HandlerResult.fail("Missing required input: context")
        if not name:
            return HandlerResult.fail("Missing required input: name")

        now = datetime.utcnow().isoformat()

        bindings = dict(seeded.get("bindings", {}))
        binding_record = {
            "value": value,
            "bound_at": now,
            "witness": str(uuid4()),
        }
        bindings[name] = binding_record

        context_type = seeded.get("context_type", "evaluation")

        extended_context: Dict[str, Any] = dict(seeded)
        # Give the extended context a fresh UUID-style id so it behaves
        # like a new recognition for persistence and linking.
        extended_context["id"] = str(uuid4())
        extended_context["bindings"] = bindings
        extended_context["context_type"] = context_type
        extended_context["act"] = act
        extended_context["acts"] = [act]
        extended_context["seeded_extended_at"] = now

        payload = ExtendFirstContextPayload(
            context_id=str(seeded.get("id", "")),
            name=name,
            binding=binding_record,
            bindings=bindings,
            context_type=context_type,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="bind-trace", children=[]),
                ActTreeNode(act="seed-first-context", children=[]),
            ],
            payload=payload.model_dump(),
        )

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(extended_context)

        return HandlerResult.ok(
            outputs={
                "context": extended_context,
                "context_id": extended_context["id"],
                "binding": binding_record,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
