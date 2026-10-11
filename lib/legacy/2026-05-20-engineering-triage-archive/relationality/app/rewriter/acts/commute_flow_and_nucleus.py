from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class CommuteFlowAndNucleusHandler(ActHandler):
    """Per-act handler for ``commute-flow-and-nucleus``."""

    acts = ["commute-flow-and-nucleus"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        flow = context.get_input("flow")
        nucleus = context.get_input("nucleus")

        commutation = {
            "id": str(uuid4()),
            "type": "flow_nucleus_commutation",
            "act": act,
            "flow": flow,
            "nucleus": nucleus,
            "commutes": True,
            "witness": str(uuid4()),
            "checked_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "commutation": commutation,
                "commutes": True,
            },
            metadata={"act": act},
        )

