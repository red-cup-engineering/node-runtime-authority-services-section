from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.rewriter.measurement_algebra import aggregate_measurements


class ProfileIntegralHandler(ActHandler):
    """Handler for the ``profile-integral`` act.

    Aggregates a collection of measurement recognitions according to
    the measurement algebra.
    """

    acts = ["profile-integral"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow()
        trace_id = str(context.trace_id)

        measurements_raw = context.get_input("measurements", [])
        aggregation_type = context.get_input("aggregation_type", "sum")

        measurements: List[Dict[str, Any]] = []
        for m in measurements_raw:
            if isinstance(m, dict):
                measurements.append(m)

        value = aggregate_measurements(measurements, aggregation_type)

        aggregate = {
            "id": str(uuid4()),
            "type": "profile_integral",
            "act": act,
            "acts": [act],
            "aggregation_type": aggregation_type,
            "count": len(measurements_raw),
            "value": value,
            "aggregated_at": now.isoformat(),
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(aggregate)

        return HandlerResult.ok(
            outputs={
                "aggregate": aggregate,
                "aggregate_id": aggregate["id"],
                "value": value,
            },
            recognitions_created=[persisted_id],
            metadata={
                "act": act,
                "aggregation_type": aggregation_type,
                "count": len(measurements_raw),
            },
        )
