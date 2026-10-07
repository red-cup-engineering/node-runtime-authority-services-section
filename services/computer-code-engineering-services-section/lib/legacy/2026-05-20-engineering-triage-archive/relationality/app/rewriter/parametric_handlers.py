"""Parametric runtime handlers.

Implements handlers for building and evolving parametric contexts
based on the parametric semantics and runtime specifications.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.context import ContextFiber, ParametricContext


class ParametricRuntimeHandler(ActHandler):
    """Handler for parametric context operations.

    Maps to acts such as: context-flow, context-nucleus, context-dynamics.
    """

    acts = ["context-flow", "context-nucleus", "context-dynamics"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        if act == "context-flow":
            # No-op placeholder for context-level flow; in a fuller
            # implementation this would apply the reindexing functors.
            pctx_in = context.get_input("parametric_context")
            if not pctx_in:
                return HandlerResult.fail("Missing required input: parametric_context")

            pctx = ParametricContext.model_validate(pctx_in)
            pctx.parameters["last_flow"] = now

            return HandlerResult.ok(
                outputs={"parametric_context": pctx.model_dump()},
                metadata={"act": act},
            )

        elif act == "context-nucleus":
            # Placeholder for context-level nucleus; could record stabilisation
            # of bindings or effects.
            pctx_in = context.get_input("parametric_context")
            if not pctx_in:
                return HandlerResult.fail("Missing required input: parametric_context")

            pctx = ParametricContext.model_validate(pctx_in)
            pctx.parameters["last_nucleus"] = now

            return HandlerResult.ok(
                outputs={"parametric_context": pctx.model_dump()},
                metadata={"act": act},
            )

        elif act == "context-dynamics":
            # Composition of flow + nucleus; we simply record a combined
            # update marker for now.
            pctx_in = context.get_input("parametric_context")
            if not pctx_in:
                return HandlerResult.fail("Missing required input: parametric_context")

            pctx = ParametricContext.model_validate(pctx_in)
            pctx.parameters["last_dynamics"] = now

            return HandlerResult.ok(
                outputs={"parametric_context": pctx.model_dump()},
                metadata={"act": act},
            )

        return HandlerResult.fail(f"Unknown parametric act: {act}")
