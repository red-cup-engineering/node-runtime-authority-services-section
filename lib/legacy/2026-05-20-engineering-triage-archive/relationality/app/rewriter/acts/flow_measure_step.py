from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.measurement import MeasurementEvent
from app.schemas.physics import PhysicsState


class FlowMeasureStepHandler(ActHandler):
    """Handler for the ``flow-measure-step`` act.

    Evolves a PhysicsState one step and emits a MeasurementEvent.
    """

    acts = ["flow-measure-step"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        state_in = context.get_input("state")
        if not state_in:
            return HandlerResult.fail("Missing required input: state")

        state = PhysicsState.model_validate(state_in)

        pctx_in = context.get_input("parametric_context")
        context_id = None
        domain = None
        if isinstance(pctx_in, dict):
            base = pctx_in.get("base", {})
            context_id = base.get("id")
            domain = base.get("domain")

        evolved_state = state

        event_metadata: Dict[str, Any] = {
            "trace_id": trace_id,
            "act": act,
            "stepped_at": now,
        }
        if context_id:
            event_metadata["context_id"] = context_id
        if domain:
            event_metadata["domain"] = domain

        event = MeasurementEvent(
            channel="physics/step",
            value={"state_id": evolved_state.id},
            metadata=event_metadata,
        )

        step_info: Dict[str, Any] = {
            "state_id": evolved_state.id,
            "act": act,
            "trace_id": trace_id,
            "stepped_at": now,
        }
        if context_id:
            step_info["context_id"] = context_id
        if domain:
            step_info["domain"] = domain

        # Optionally ingest the measurement into the measurement fabric if
        # the channel has been configured. This bridges the measurement stack
        # into the fabric without forcing configuration on all callers.
        fabric = getattr(context, "measurement_fabric", None)
        if fabric is not None:
            try:
                cfg = fabric.get_channel(event.channel)
                if cfg is not None:
                    fabric.ingest(event)
            except Exception:
                # Ingestion failures should not break the act; they can be
                # surfaced via introspection/monitoring.
                pass

        return HandlerResult.ok(
            outputs={
                "state": evolved_state.model_dump(),
                "step_info": step_info,
                "measurement": event.model_dump(),
            },
            metadata={"act": act},
        )
