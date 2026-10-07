"""Policy schema definitions.

Policies implement the discipline/filter/governance rules from the policy stack.
They control which recognitions can enter the system and which runbook steps
can execute based on tags, acts, and authorization levels.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class PolicyEffect(str, Enum):
    """Effect of a policy rule match."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyScope(str, Enum):
    """Scope of policy application."""
    RECOGNITION = "recognition"
    RUNBOOK = "runbook"
    STEP = "step"
    SNAPSHOT = "snapshot"
    GLOBAL = "global"


class DisciplineRule(BaseModel):
    """A discipline rule that constrains what data may flow.
    
    Disciplines are composable filters that apply to recognitions
    based on their tags, acts, and content patterns.
    """
    
    id: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_-]*$",
        description="Unique rule identifier"
    )
    
    name: str = Field(..., min_length=1, max_length=128)
    
    description: Optional[str] = None
    
    match_tags: list[str] = Field(
        default_factory=list,
        description="Tags that must be present for this rule to apply"
    )
    
    match_acts: list[str] = Field(
        default_factory=list,
        description="Acts that trigger this rule"
    )
    
    match_types: list[str] = Field(
        default_factory=list,
        description="Recognition types this rule applies to"
    )
    
    effect: PolicyEffect = Field(
        default=PolicyEffect.ALLOW,
        description="What happens when the rule matches"
    )
    
    priority: int = Field(
        default=100,
        ge=0,
        le=1000,
        description="Higher priority rules are evaluated first"
    )


class FilterRule(BaseModel):
    """A filter rule that transforms or restricts content.
    
    Filters can mask fields, require specific patterns, or
    transform content before admission.
    """
    
    id: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_-]*$",
        description="Unique filter identifier"
    )
    
    name: str = Field(..., min_length=1, max_length=128)
    
    description: Optional[str] = None
    
    match_path: str = Field(
        default="*",
        description="JSONPath pattern for content fields to filter"
    )
    
    action: str = Field(
        default="mask",
        description="Filter action: mask, require, transform, remove"
    )
    
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters"
    )
    
    applies_to_scope: PolicyScope = Field(
        default=PolicyScope.RECOGNITION
    )


class PolicyAnnotation(BaseModel):
    """A policy annotation that authorizes operations.
    
    Annotations are attached to recognitions or runbook executions
    to prove that required policies have been satisfied.
    """
    
    id: UUID = Field(default_factory=uuid4)
    
    policy_id: str = Field(
        ...,
        description="ID of the policy this annotation satisfies"
    )
    
    scope: PolicyScope = Field(default=PolicyScope.RECOGNITION)
    
    granted_by: str = Field(
        ...,
        description="Identity that granted this authorization"
    )
    
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When this authorization expires"
    )
    
    conditions: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional conditions for this authorization"
    )
    
    justification: Optional[str] = Field(
        default=None,
        description="Human-readable reason for granting access"
    )


class PolicyDefinition(BaseModel):
    """Complete policy definition combining disciplines and filters."""
    
    id: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_-]*$",
        description="Unique policy identifier"
    )
    
    name: str = Field(..., min_length=1, max_length=256)
    
    description: Optional[str] = None
    
    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$"
    )
    
    scope: PolicyScope = Field(default=PolicyScope.RECOGNITION)
    
    disciplines: list[DisciplineRule] = Field(
        default_factory=list,
        description="Discipline rules in this policy"
    )
    
    filters: list[FilterRule] = Field(
        default_factory=list,
        description="Filter rules in this policy"
    )
    
    default_effect: PolicyEffect = Field(
        default=PolicyEffect.DENY,
        description="Effect when no rules match"
    )
    
    tags: list[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator("disciplines")
    @classmethod
    def validate_unique_discipline_ids(cls, v: list[DisciplineRule]) -> list[DisciplineRule]:
        ids = [d.id for d in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Discipline IDs must be unique within a policy")
        return v
    
    @field_validator("filters")
    @classmethod
    def validate_unique_filter_ids(cls, v: list[FilterRule]) -> list[FilterRule]:
        ids = [f.id for f in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Filter IDs must be unique within a policy")
        return v


class PolicyDecision(BaseModel):
    """Result of evaluating a policy against a target."""
    
    policy_id: str
    target_id: str
    effect: PolicyEffect
    matched_rules: list[str] = Field(default_factory=list)
    applied_filters: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    reasoning: Optional[str] = None


def validate_policy(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a policy definition.
    
    Args:
        data: The policy data to validate.
    
    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: list[str] = []
    
    try:
        PolicyDefinition.model_validate(data)
    except Exception as e:
        return False, [str(e)]
    
    return len(errors) == 0, errors
