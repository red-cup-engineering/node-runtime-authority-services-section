from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SampleObservableHandler(ActHandler):
    """Helper for sampling observables for diagnostics.

    This is not a first-class act; it is a utility that may be called
    directly by internal tooling or interfaces.
    """

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        observable = context.get_input("observable")
        sample_rate = context.get_input("sample_rate", 1.0)

        sample = {
            "id": str(uuid4()),
            "type": "observable_sample",
            "act": act,
            "observable": observable,
            "sample_rate": sample_rate,
            "sampled": True,
            "sampled_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "sample": sample,
                "sampled": True,
            },
            metadata={"act": act, "sample_rate": sample_rate},
        )
