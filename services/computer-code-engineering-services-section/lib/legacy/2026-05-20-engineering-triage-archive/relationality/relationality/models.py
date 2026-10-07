"""
Pydantic models and runtime dataclasses derived directly from the README
specification. These models mirror the persistent layer (objects, runbooks,
realizers) and the runtime interaction surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecognitionObject(BaseModel):
    """Frozen recognition-carrier mapped from acts → objects."""

    id: str
    kind: str
    payload: Dict[str, Any]
    acts: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class RealizerSpec(BaseModel):
    """Metadata describing an act-level operator kernel."""

    id: str
    act: str
    module: str
    callable: str
    input_kind: str
    output_kind: str
    invariants: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class RunbookStep(BaseModel):
    """Single operator step within a runbook."""

    operator: str
    realizer: str
    input_kind: str
    output_kind: str
    invariants: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    acts: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class RunbookSpec(BaseModel):
    """Declarative morphic pipeline (acts → runbook)."""

    id: str
    name: str
    input_kind: str
    output_kind: str
    steps: List[RunbookStep]
    description: Optional[str] = None
    acts: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


@dataclass
class RealizerContext:
    """Runtime context provided to realizers (acts → moves)."""

    runbook_id: str
    step: RunbookStep
    system_id: Optional[str] = None
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class InteractionRequest(BaseModel):
    """External interaction payload for POST /system/{id}/interact."""

    observation: Dict[str, Any]
    intent: str = "default"
    constraints: Optional[Dict[str, Any]] = None
    trace_context: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class OperatorDiagnostics(BaseModel):
    flow_nucleus_commutation: str
    operators_used: List[str]
    spectral_effects: Dict[str, Any] = Field(default_factory=dict)
    invariants_checked: List[str] = Field(default_factory=list)
    commutation_evidence: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class InteractionResponse(BaseModel):
    fixed_invariant: Dict[str, Any]
    updated_trace: Dict[str, Any]
    updated_phase_space: Dict[str, Any]
    updated_fixed_invariants: Dict[str, Any]
    operator_diagnostics: OperatorDiagnostics

    model_config = ConfigDict(extra="forbid")
