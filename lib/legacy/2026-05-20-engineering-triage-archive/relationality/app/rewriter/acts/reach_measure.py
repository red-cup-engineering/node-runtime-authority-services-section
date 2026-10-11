from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ReachMeasureHandler(ActHandler):
    """Per-act handler for ``reach-measure``."""

    acts = ["reach-measure"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        source = context.get_input("source")
        target = context.get_input("target")

        measure = {
            "id": str(uuid4()),
            "type": "reach_measure",
            "act": act,
            "source": source,
            "target": target,
            "distance": 0,
            "measured_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "measure": measure,
                "distance": 0,
            },
            metadata={"act": act},
        )

