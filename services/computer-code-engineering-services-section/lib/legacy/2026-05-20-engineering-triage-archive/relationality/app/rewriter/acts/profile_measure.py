from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.rewriter.measurement_algebra import measure_observable
from app.schemas.measurement import MeasurementEvent


class ProfileMeasureHandler(ActHandler):
    """Handler for the ``profile-measure`` act.

    Measures an observable on a target within a profile, producing
    a measurement recognition.
    """

    acts = ["profile-measure"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow()
        trace_id = str(context.trace_id)

        target = context.get_input("target")
        observable_type = context.get_input("observable_type", "count")
        channel = context.get_input("channel", f"profile/{observable_type}")

        value = measure_observable(target, observable_type)

        event = MeasurementEvent(
            channel=channel,
            value=value,
            ts=now,
            metadata={
                "act": act,
                "observable_type": observable_type,
                "trace_id": trace_id,
            },
        )

        persisted_id = await context.persist_recognition(
            {
                "id": str(uuid4()),
                "type": "measurement_event",
                "act": act,
                "acts": [act],
                "event": event.model_dump(),
            }
        )

        return HandlerResult.ok(
            outputs={
                "measurement": event.model_dump(),
                "measurement_id": str(persisted_id),
                "value": value,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "observable_type": observable_type},
        )
