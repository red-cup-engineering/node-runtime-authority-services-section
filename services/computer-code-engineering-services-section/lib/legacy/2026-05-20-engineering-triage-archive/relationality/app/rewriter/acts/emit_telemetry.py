from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.measurement import MeasurementEvent


class EmitTelemetryHandler(ActHandler):
    """Helper for emitting telemetry into the measurement fabric.

    This is not a first-class act; it is a utility that may be called
    directly by internal tooling or interfaces.
    """

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        event_type = context.get_input("event_type", "generic")
        event_data = context.get_input("event_data", {})

        telemetry = {
            "id": str(uuid4()),
            "type": "telemetry",
            "act": act,
            "event_type": event_type,
            "event_data": event_data,
            "emitted_at": now,
            "trace_id": trace_id,
        }

        # Optionally reflect telemetry into the measurement fabric as a
        # measurement event on a channel derived from the event type.
        fabric = getattr(context, "measurement_fabric", None)
        if fabric is not None:
            try:
                channel = f"telemetry/{event_type}"
                event = MeasurementEvent(
                    channel=channel,
                    value=event_data,
                    metadata={
                        "trace_id": trace_id,
                        "act": act,
                        "emitted_at": now,
                        "event_type": event_type,
                    },
                )
                cfg = fabric.get_channel(channel)
                if cfg is not None:
                    fabric.ingest(event)
            except Exception:
                # Ingestion failures should not break telemetry emission.
                pass

        return HandlerResult.ok(
            outputs={
                "telemetry": telemetry,
                "telemetry_id": telemetry["id"],
            },
            metadata={"act": act, "event_type": event_type},
        )
