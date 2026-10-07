from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.term_family import TermFamilyPayload
from app.schemas.fibers.registry import register_fiber
from app.schemas.stlc import TermAST
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ConstructTermsHandler(ActHandler):
    """Per-act handler for ``construct-terms``.

    Collects a family of earned term recognitions (from form-function-term
    and form-application-term) into a constructed term family. This
    realises the *Construct Terms* act whose ingredients are the
    function and application term formers.

    Inputs:
      - terms: list[dict] (required) – term recognitions or descriptors.
    """

    acts = ["construct-terms"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        terms: List[Dict[str, Any]] | None = context.get_input("terms")
        if not terms:
            return HandlerResult.fail("Missing required input: terms")

        # Interpret the provided payloads as STLC term ASTs.
        term_asts: List[TermAST] = []
        for t in terms:
            # Accept either bare STLC terms or full term recognitions
            if isinstance(t, dict):
                if "kind" in t:
                    term_asts.append(TermAST.model_validate(t))
                elif "body" in t:
                    term_asts.append(TermAST.model_validate(t["body"]))
                elif "application" in t:
                    term_asts.append(TermAST.model_validate(t["application"]))
            elif isinstance(t, TermAST):
                term_asts.append(t)

        if not term_asts:
            return HandlerResult.fail("No terms provided; expected at least one TermAST")

        payload = TermFamilyPayload(terms=term_asts)

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="form-function-term", children=[]),
                ActTreeNode(act="form-application-term", children=[]),
            ],
            payload=payload.model_dump(),
        )

        constructed = fibre.model_dump(mode="json")
        constructed["type"] = "context"
        constructed["title"] = "Constructed terms"
        constructed["act"] = act
        constructed["terms"] = [t.model_dump() for t in term_asts]
        constructed["constructed_at"] = datetime.utcnow().isoformat()
        constructed["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(constructed)

        return HandlerResult.ok(
            outputs={"constructed_terms": constructed, "terms": constructed["terms"]},
            recognitions_created=[persisted_id],
            metadata={"act": act, "count": len(term_asts)},
        )
