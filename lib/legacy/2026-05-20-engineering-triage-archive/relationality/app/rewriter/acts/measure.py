from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.rewriter.measurement_algebra import compute_expectation


class MeasureHandler(ActHandler):
    """Handler for the ``measure`` act.

    Encodes the expectation computation from the measurement algebra
    specification as a concrete act over recognitions.
    """

    acts = ["measure"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        observable = context.get_input("observable")
        distribution = context.get_input("distribution", {})

        if observable is None:
            return HandlerResult.fail("Missing required input: observable")

        value = compute_expectation(observable, distribution)

        expectation = {
            "id": str(uuid4()),
            "type": "expectation",
            "act": act,
            "acts": [act],
            "observable": observable,
            "distribution": distribution,
            "value": value,
            "computed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(expectation)

        return HandlerResult.ok(
            outputs={
                "expectation": expectation,
                "expectation_id": expectation["id"],
                "value": value,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

