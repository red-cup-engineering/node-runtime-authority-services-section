from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.function_term import FunctionTermPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class FormFunctionTermHandler(ActHandler):
    """Per-act handler for ``form-function-term``.

    Runtime reflection of *Form Function Term*: the composition
    `(FormTermBody TraceContext)`, turning a term body and a trace
    context into a function term.

    Inputs:
      - body: any (required) – term body descriptor
      - trace_context: any (required) – context/trace descriptor
    """

    acts = ["form-function-term"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        body = context.get_input("body")
        trace_context = context.get_input("trace_context")

        if body is None:
            return HandlerResult.fail("Missing required input: body")
        if trace_context is None:
            return HandlerResult.fail("Missing required input: trace_context")

        payload = FunctionTermPayload(body=body, trace_context=trace_context)

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="form-term-body", children=[]),
                ActTreeNode(act="trace-context", children=[]),
            ],
            payload=payload.model_dump(),
        )

        term: Dict[str, Any] = fibre.model_dump(mode="json")
        term["type"] = "term"
        term["title"] = "Function term"
        term["act"] = act
        term["arity"] = 2
        term["body"] = body
        term["trace_context"] = trace_context
        term["constructed_at"] = datetime.utcnow().isoformat()
        term["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(term)

        return HandlerResult.ok(
            outputs={
                "function_term": term,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
