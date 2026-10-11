from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.context import Context, ContextFiber, ParametricContext


class BuildContextHandler(ActHandler):
    """Handler for building a base parametric evaluation context.

    Realises the *Build Evaluation Context* act at the parametric runtime
    level.
    """

    acts = ["build-evaluation-context"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        tenant = context.get_input("tenant")
        domain = context.get_input("domain")
        profile_id = context.get_input("profile_id")
        metadata = context.get_input("metadata", {})

        ctx = Context(
            id=str(uuid4()),
            tenant=tenant,
            domain=domain,
            profile_id=profile_id,
            metadata={**metadata, "trace_id": trace_id, "built_at": now},
        )

        fibre = ContextFiber(
            id=str(uuid4()),
            context_id=ctx.id,
            bindings={},
            metadata={"trace_id": trace_id, "created_at": now},
        )

        pctx = ParametricContext(base=ctx, fibre=fibre, parameters={})

        return HandlerResult.ok(
            outputs={
                "context": ctx.model_dump(),
                "fibre": fibre.model_dump(),
                "parametric_context": pctx.model_dump(),
            },
            metadata={"act": act},
        )
