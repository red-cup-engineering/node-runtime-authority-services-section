from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class BindTermHandler(ActHandler):
    """Per-act handler for ``bind-term``."""

    acts = ["bind-term"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        term = context.get_input("term")
        variable = context.get_input("variable")
        value = context.get_input("value")

        if term is None:
            return HandlerResult.fail("Missing required input: term")
        if not variable:
            return HandlerResult.fail("Missing required input: variable")

        binding = {
            "id": str(uuid4()),
            "type": "term_binding",
            "act": act,
            "term": term,
            "variable": variable,
            "value": value,
            "bound_at": now,
            "trace_id": trace_id,
        }

        bound_term = (
            {**term, variable: value} if isinstance(term, dict) else term
        )

        return HandlerResult.ok(
            outputs={
                "binding": binding,
                "bound_term": bound_term,
            },
            metadata={"act": act, "variable": variable},
        )

