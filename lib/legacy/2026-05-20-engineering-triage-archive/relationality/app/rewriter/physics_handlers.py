"""Physics simulation handlers.

Implements handlers for profile-level physics evolution and
simulation runs based on the earned physics acts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.physics import PhysicsState, PhysicsScenario, SimulationRun
from app.schemas.measurement import MeasurementEvent


class PhysicsRuntimeHandler(ActHandler):
    """Handler for physics state evolution.

    Maps to acts such as: physics-state, flow-measure-step.
    """

    acts = ["physics-state", "flow-measure-step"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        if act == "physics-state":
            # Wrap a set of recognition ids into a PhysicsState.
            recognition_ids = context.get_input("recognition_ids", [])
            profile_id = context.get_input("profile_id")

            state = PhysicsState(
                id=str(uuid4()),
                profile_id=profile_id,
                recognition_ids=[str(rid) for rid in recognition_ids],
                metadata={
                    "trace_id": trace_id,
                    "constructed_at": now,
                },
            )

            return HandlerResult.ok(
                outputs={"state": state.model_dump()},
                metadata={"act": act},
            )

        elif act == "flow-measure-step":
            # Evolve a physics state one step and emit a measurement event.
            # We do NOT persist a TracePoint here; persistence should happen
            # via intake/measurement runbooks (recognize-observation, etc.).
            state_in = context.get_input("state")
            if not state_in:
                return HandlerResult.fail("Missing required input: state")

            state = PhysicsState.model_validate(state_in)

            # TODO: apply actual dynamics based on PhysicsDynamics; for now we
            # simply record a no-op evolution step.
            evolved_state = state

            # Construct a simple measurement event for this step.
            event = MeasurementEvent(
                channel="physics/step",
                value={"state_id": evolved_state.id},
                metadata={"trace_id": trace_id, "act": act, "stepped_at": now},
            )

            step_info: dict[str, Any] = {
                "state_id": evolved_state.id,
                "act": act,
                "trace_id": trace_id,
                "stepped_at": now,
            }

            return HandlerResult.ok(
                outputs={
                    "state": evolved_state.model_dump(),
                    "step_info": step_info,
                    "measurement": event.model_dump(),
                },
                metadata={"act": act},
            )

        return HandlerResult.fail(f"Unknown physics act: {act}")


class PhysicsSimulationHandler(ActHandler):
    """Handler for orchestrating a full physics SimulationRun."""

    acts = ["run-physics-scenario"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        if act != "run-physics-scenario":
            return HandlerResult.fail(f"Unknown physics simulation act: {act}")

        scenario_in = context.get_input("scenario")
        if not scenario_in:
            return HandlerResult.fail("Missing required input: scenario")

        scenario = PhysicsScenario.model_validate(scenario_in)

        run = SimulationRun(
            scenario_id=scenario.id,
            started_at=datetime.utcnow(),
        )

        # For now, just record the initial state id; a fuller implementation
        # would iterate dynamics acts and record intermediate states and
        # measurement event ids.
        run.state_ids.append(scenario.initial_state.id)
        run.completed_at = datetime.utcnow()

        return HandlerResult.ok(
            outputs={"run": run.model_dump()},
            metadata={"act": act},
        )
