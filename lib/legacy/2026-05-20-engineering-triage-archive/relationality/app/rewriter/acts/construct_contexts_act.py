from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.context_family import ContextFamilyPayload
from app.schemas.fibers.registry import register_fiber
from app.schemas.stlc import TypeAST, TypingContext, TypingContextEntry
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ConstructContextsHandler(ActHandler):
    """Per-act handler for ``construct-contexts``.

    Builds contexts as traced collections of types.

    Inputs:
      - types: list[dict] (required) – type descriptors.
    """

    acts = ["construct-contexts"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        types: List[Dict[str, Any]] | None = context.get_input("types")
        if not types:
            return HandlerResult.fail("Missing required input: types")

        # Build a single typing context from the supplied type atoms,
        # assigning schematic variable names x0, x1, ...
        entries: List[TypingContextEntry] = []
        for idx, t in enumerate(types):
            if not isinstance(t, dict):
                continue
            type_ast = TypeAST.model_validate(t)
            entries.append(
                TypingContextEntry(
                    var=f"x{idx}",
                    type=type_ast,
                )
            )

        context_ast = TypingContext(entries=entries)
        payload = ContextFamilyPayload(contexts=[context_ast])

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="contextualize-trace", children=[]),
                ActTreeNode(act="construct-types", children=[]),
            ],
            payload=payload.model_dump(),
        )

        constructed = fibre.model_dump(mode="json")
        constructed["type"] = "context"
        constructed["title"] = "Constructed contexts"
        constructed["act"] = act
        constructed["types"] = types
        constructed["contexts"] = [context_ast.model_dump()]
        constructed["constructed_at"] = datetime.utcnow().isoformat()
        constructed["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(constructed)

        return HandlerResult.ok(
            outputs={"constructed_contexts": constructed},
            recognitions_created=[persisted_id],
            metadata={"act": act, "count": len(types)},
        )
