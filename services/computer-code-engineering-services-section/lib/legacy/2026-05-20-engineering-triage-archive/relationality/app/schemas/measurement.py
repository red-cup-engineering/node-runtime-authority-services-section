"""Measurement-related schemas.

These datatypes correspond to the state described in the measurement
fabric and measurement algebra specifications: observables and their
values on channels over time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MeasurementEvent(BaseModel):
    """A single measurement event on a channel.

    This is intentionally generic: the measurement algebra and fabric
    specs describe observables and measures in many forms. Here we
    capture the common structure used by the runtime:

    - `channel`: which logical channel this event belongs to,
    - `value`: numeric or structured value,
    - `ts`: timestamp of the measurement,
    - `metadata`: additional context (e.g., source module, tags).
    """

    channel: str = Field(
        ...,
        description="Logical measurement channel identifier",
    )

    value: Union[float, int, Dict[str, Any], List[Any]] = Field(
        ...,
        description="Measured value (numeric or structured)",
    )

    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the measurement event",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the measurement",
    )


class ObservableSchema(BaseModel):
    """Schema for a single observable/measurement channel.

    Captures the semantic envelope for a measurement stream:

    - canonical name / channel id,
    - units and optional numeric bounds,
    - tags for downstream routing/policy,
    - free-form metadata for additional context.
    """

    name: str = Field(..., description="Canonical observable name")
    unit: Optional[str] = Field(
        default=None,
        description="Unit for the observable (e.g., ms, bytes, count)",
    )
    lower_bound: Optional[float] = Field(
        default=None,
        description="Optional lower bound for numeric values",
    )
    upper_bound: Optional[float] = Field(
        default=None,
        description="Optional upper bound for numeric values",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Classification tags for routing/policy",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional schema metadata",
    )


class ChannelConfig(BaseModel):
    """Configuration entry for a measurement channel in the fabric."""

    channel: str = Field(..., description="Channel identifier")
    schema_name: str = Field(..., description="Name of the observable schema")
    subscribers: List[str] = Field(
        default_factory=list,
        description="Logical subscribers (module names, services, etc.)",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntrospectionSummary(BaseModel):
    """Summary statistics for a measurement stream."""

    channel: str = Field(..., description="Channel identifier")
    count: int = Field(0, description="Number of events seen")
    last_ts: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the most recent event",
    )
    aggregates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregate metrics (rolling averages, quantiles, etc.)",
    )
