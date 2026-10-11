from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class IntrospectContextHandler(ActHandler):
    """Helper for inspecting parametric/trace contexts.

    This is not a first-class act; it is a utility that may be called
    directly by internal tooling or interfaces.
    """

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        ctx = context.get_input("context")
        include_bindings = context.get_input("include_bindings", True)

        if not ctx:
            return HandlerResult.fail("Missing required input: context")

        now = datetime.utcnow().isoformat()
        bindings = ctx.get("bindings", {}) if include_bindings else {}

        introspection = {
            "id": str(uuid4()),
            "type": "context_introspection",
            "act": act,
            "context_id": ctx.get("id"),
            "context_type": ctx.get("context_type"),
            "depth": ctx.get("depth", 0),
            "binding_count": len(bindings),
            "bindings": bindings,
            "introspected_at": now,
        }

        return HandlerResult.ok(
            outputs={
                "introspection": introspection,
                "binding_count": introspection["binding_count"],
            },
            metadata={"act": act},
        )
