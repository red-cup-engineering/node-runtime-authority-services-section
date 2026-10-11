from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.type_family import TypeFamilyPayload
from app.schemas.fibers.registry import register_fiber
from app.schemas.stlc import TypeAST
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ConstructTypesHandler(ActHandler):
    """Per-act handler for ``construct-types``.

    Collects a family of earned type witnesses (from meet/join/imply
    recognition acts) into a constructed type family. This realises
    the *Construct Types* act whose ingredients are Meet Recognition
    and Imply Recognition.

    Inputs:
      - types: list[dict] (required) – type descriptors.
    """

    acts = ["construct-types"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        types: List[Dict[str, Any]] | None = context.get_input("types")
        if not types:
            return HandlerResult.fail("Missing required input: types")

        # Interpret the provided payloads as STLC type ASTs.
        type_asts: List[TypeAST] = []
        for t in types:
            if isinstance(t, dict) and "kind" in t:
                type_asts.append(TypeAST.model_validate(t))
            elif isinstance(t, TypeAST):
                type_asts.append(t)

        if not type_asts:
            return HandlerResult.fail("No types provided; expected at least one TypeAST")

        payload = TypeFamilyPayload(types=type_asts)

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="meet-recognition", children=[]),
                ActTreeNode(act="imply-recognition", children=[]),
            ],
            payload=payload.model_dump(),
        )

        constructed = fibre.model_dump(mode="json")
        constructed["type"] = "context"
        constructed["title"] = "Constructed types"
        constructed["act"] = act
        constructed["types"] = [t.model_dump() for t in type_asts]
        constructed["constructed_at"] = datetime.utcnow().isoformat()
        constructed["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(constructed)

        return HandlerResult.ok(
            outputs={"constructed_types": constructed, "types": constructed["types"]},
            recognitions_created=[persisted_id],
            metadata={"act": act, "count": len(type_asts)},
        )
