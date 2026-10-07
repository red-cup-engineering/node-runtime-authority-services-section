from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class DirectedTransportHandler(ActHandler):
    """Directed space helper (not a core act)."""

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        source = context.get_input("source")
        path: List[Any] = context.get_input("path", [])

        if source is None:
            return HandlerResult.fail("Missing required input: source")

        transport = {
            "id": str(uuid4()),
            "type": "directed_transport",
            "act": act,
            "source": source,
            "path": path,
            "path_length": len(path),
            "transported_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "transport": transport,
                "transport_id": transport["id"],
            },
            metadata={"act": act, "path_length": len(path)},
        )
