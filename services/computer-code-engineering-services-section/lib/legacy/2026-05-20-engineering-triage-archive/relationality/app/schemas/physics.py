"""Physics simulation schemas.

These datatypes capture states, scenarios, and runs for physics
simulations built from the earned physics and measurement stacks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PhysicsState(BaseModel):
    """Profile-level physics state.

    Represents a stabilized slice of the profile/tower carrying
    physics recognitions (positions, fields, etc.), plus metadata
    about the flow/nucleus regime.
    """

    id: str = Field(..., description="State identifier")
    profile_id: Optional[str] = Field(
        default=None,
        description="Profile/tower identifier this state belongs to",
    )
    recognition_ids: List[str] = Field(
        default_factory=list,
        description="IDs of recognitions that constitute this state",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flow/nucleus parameters, regime info, etc.",
    )


class PhysicsDynamics(BaseModel):
    """Dynamics specification for a physics simulation."""

    acts: List[str] = Field(
        ...,
        description="Sequence of physics acts (evolve, flow-observation, etc.)",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamics parameters (step size, regime flags, etc.)",
    )


class PhysicsScenario(BaseModel):
    """Scenario for a physics simulation run."""

    id: str = Field(..., description="Scenario identifier")
    initial_state: PhysicsState
    dynamics: PhysicsDynamics
    steps: int = Field(..., description="Number of evolution steps")
    sample_every: int = Field(
        1,
        description="How often to record measurements (in steps)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional scenario metadata",
    )


class SimulationRun(BaseModel):
    """Result of executing a physics scenario."""

    scenario_id: str = Field(..., description="ID of the scenario run")
    state_ids: List[str] = Field(
        default_factory=list,
        description="Sequence of PhysicsState ids visited",
    )
    measurement_ids: List[str] = Field(
        default_factory=list,
        description="IDs of MeasurementEvent TracePoints emitted",
    )
    invariants: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results of invariant checks keyed by name",
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Run start time",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Run completion time",
    )

