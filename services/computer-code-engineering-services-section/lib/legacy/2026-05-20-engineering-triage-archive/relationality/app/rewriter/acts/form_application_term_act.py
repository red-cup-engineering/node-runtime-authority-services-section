from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.application_term import ApplicationTermPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class FormApplicationTermHandler(ActHandler):
    """Per-act handler for ``form-application-term``.

    Runtime reflection of *Form Application Term*: the composition
    `(PairApplication TailTrace)`, turning a function/argument pair and
    a tail trace into an application term.

    Inputs:
      - application: any (required) – descriptor of the application (function/arg)
      - tail: any (required) – descriptor of the remaining trace/body
    """

    acts = ["form-application-term"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        application = context.get_input("application")
        tail = context.get_input("tail")

        if application is None:
            return HandlerResult.fail("Missing required input: application")
        if tail is None:
            return HandlerResult.fail("Missing required input: tail")

        payload = ApplicationTermPayload(application=application, tail=tail)

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="pair-application", children=[]),
                ActTreeNode(act="tail-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        term: Dict[str, Any] = fibre.model_dump(mode="json")
        term["type"] = "term"
        term["title"] = "Application term"
        term["act"] = act
        term["arity"] = 2
        term["application"] = application
        term["tail"] = tail
        term["constructed_at"] = datetime.utcnow().isoformat()
        term["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(term)

        return HandlerResult.ok(
            outputs={
                "application_term": term,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
