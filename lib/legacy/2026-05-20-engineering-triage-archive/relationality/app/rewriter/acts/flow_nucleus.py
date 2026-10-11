from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class FlowNucleusHandler(ActHandler):
    """Per-act handler for ``fix-flow-nucleus``."""

    acts = ["fix-flow-nucleus"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        flow = context.get_input("flow")
        nucleus_type = context.get_input("nucleus_type", "standard")

        nucleus = {
            "id": str(uuid4()),
            "type": "flow_nucleus",
            "act": act,
            "flow": flow,
            "nucleus_type": nucleus_type,
            "computed_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "nucleus": nucleus,
                "nucleus_id": nucleus["id"],
            },
            metadata={"act": act, "nucleus_type": nucleus_type},
        )
