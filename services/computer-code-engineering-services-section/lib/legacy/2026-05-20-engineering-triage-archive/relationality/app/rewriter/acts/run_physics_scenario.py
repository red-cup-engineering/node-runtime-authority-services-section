from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.physics import PhysicsState, PhysicsDynamics, PhysicsScenario, SimulationRun


class RunPhysicsScenarioHandler(ActHandler):
    """Handler for the ``run-physics-scenario`` act.

    Orchestrates a SimulationRun from physics state + dynamics inputs.
    """

    acts = ["run-physics-scenario"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        scenario_id = context.get_input("scenario_id")
        initial_state_in = context.get_input("initial_state")
        dynamics_acts = context.get_input("dynamics_acts", [])
        dynamics_parameters = context.get_input("dynamics_parameters", {})
        steps = context.get_input("steps", 1)
        sample_every = context.get_input("sample_every", 1)
        metadata = context.get_input("metadata", {})

        if not initial_state_in:
            return HandlerResult.fail("Missing required input: initial_state")

        initial_state = PhysicsState.model_validate(initial_state_in)

        if not dynamics_acts:
            return HandlerResult.fail("Missing required input: dynamics_acts")

        dynamics = PhysicsDynamics(
            acts=list(dynamics_acts),
            parameters=dynamics_parameters or {},
        )

        if not scenario_id:
            scenario_id = f"scenario-{uuid4()}"

        scenario = PhysicsScenario(
            id=scenario_id,
            initial_state=initial_state,
            dynamics=dynamics,
            steps=int(steps),
            sample_every=int(sample_every),
            metadata=metadata or {},
        )

        run = SimulationRun(
            scenario_id=scenario.id,
            started_at=datetime.utcnow(),
        )

        run.state_ids.append(initial_state.id)
        run.completed_at = datetime.utcnow()

        return HandlerResult.ok(
            outputs={
                "scenario": scenario.model_dump(),
                "run": run.model_dump(),
            },
            metadata={"act": act},
        )
