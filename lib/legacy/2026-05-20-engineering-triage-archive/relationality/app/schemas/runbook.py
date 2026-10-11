"""Runbook schema definitions.

A Runbook is a sequence of steps that map to acts in the relational calculus.
Each step must trace back to earned mathematics, ensuring every operation
is formally justified.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class StepStatus(str, Enum):
    """Execution status of a runbook step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunbookStatus(str, Enum):
    """Overall status of a runbook."""
    DRAFT = "draft"
    VALIDATED = "validated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepInput(BaseModel):
    """Input specification for a runbook step."""
    
    name: str = Field(..., description="Input parameter name")
    type: str = Field(default="any", description="Expected type (any, string, number, recognition, etc.)")
    required: bool = Field(default=True)
    default: Optional[Any] = None
    from_step: Optional[str] = Field(
        default=None,
        description="Reference to output from a previous step (step_id.output_name)"
    )


class StepOutput(BaseModel):
    """Output specification for a runbook step."""
    
    name: str = Field(..., description="Output parameter name")
    type: str = Field(default="any", description="Output type")
    description: Optional[str] = None


class RunbookStep(BaseModel):
    """A single step in a runbook, mapped to one or more acts."""
    
    id: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_-]*$",
        description="Unique step identifier within the runbook"
    )
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Human-readable step name"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Detailed description of what this step does"
    )
    
    acts: list[str] = Field(
        ...,
        min_length=1,
        description="List of act slugs this step executes (e.g., ['seed-observation', 'recognize-value'])"
    )
    
    depends_on: list[str] = Field(
        default_factory=list,
        description="List of step IDs that must complete before this step"
    )
    
    inputs: list[StepInput] = Field(
        default_factory=list,
        description="Input parameters for this step"
    )
    
    outputs: list[StepOutput] = Field(
        default_factory=list,
        description="Output parameters produced by this step"
    )
    
    condition: Optional[str] = Field(
        default=None,
        description="Optional condition expression (Python-like) that must be true to run"
    )
    
    retry_count: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Number of retry attempts on failure"
    )
    
    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Maximum execution time in seconds"
    )
    
    @field_validator("acts")
    @classmethod
    def validate_acts_format(cls, v: list[str]) -> list[str]:
        for act in v:
            if not act.replace("-", "").replace("_", "").isalnum():
                raise ValueError(f"Invalid act slug format: {act}")
        return v


class RunbookCreate(BaseModel):
    """Schema for creating a new runbook."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Runbook name"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Runbook description"
    )
    
    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version"
    )
    
    steps: list[RunbookStep] = Field(
        ...,
        min_length=1,
        description="Ordered list of steps"
    )
    
    tags: list[str] = Field(
        default_factory=list,
        description="Classification tags"
    )
    
    policy_requirements: list[str] = Field(
        default_factory=list,
        description="Policy annotations required to execute this runbook"
    )
    
    @model_validator(mode="after")
    def validate_step_dependencies(self: "RunbookCreate") -> "RunbookCreate":
        """Ensure step dependencies are well-formed and acyclic."""
        step_ids = {step.id for step in self.steps}
        
        for step in self.steps:
            unknown_deps = set(step.depends_on) - step_ids
            if unknown_deps:
                raise ValueError(f"Step '{step.id}' depends on unknown steps: {unknown_deps}")
        
        visited: set[str] = set()
        rec_stack: set[str] = set()
        step_map = {s.id: s for s in self.steps}
        
        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            for dep in step_map[step_id].depends_on:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(step_id)
            return False
        
        for step in self.steps:
            if step.id not in visited:
                if has_cycle(step.id):
                    raise ValueError(f"Circular dependency detected involving step '{step.id}'")
        
        return self


class RunbookSchema(RunbookCreate):
    """Full runbook schema including system-managed fields."""
    
    id: UUID = Field(default_factory=uuid4)
    
    status: RunbookStatus = Field(default=RunbookStatus.DRAFT)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    created_by: Optional[str] = Field(default=None)
    
    last_execution_id: Optional[UUID] = Field(default=None)
    
    execution_count: int = Field(default=0)
    
    class Config:
        from_attributes = True


def validate_runbook(data: dict[str, Any], known_acts: set[str]) -> tuple[bool, list[str]]:
    """Validate a runbook payload against the schema and known acts.
    
    Args:
        data: The runbook data to validate.
        known_acts: Set of known act slugs from the graph.
    
    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: list[str] = []
    
    try:
        runbook = RunbookCreate.model_validate(data)
    except Exception as e:
        return False, [str(e)]
    
    all_acts: set[str] = set()
    for step in runbook.steps:
        all_acts.update(step.acts)
    
    unknown_acts = all_acts - known_acts
    if unknown_acts:
        errors.append(f"Unknown acts referenced: {sorted(unknown_acts)}")
    
    return len(errors) == 0, errors
