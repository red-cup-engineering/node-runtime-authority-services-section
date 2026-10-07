from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.schemas.measurement import (
    MeasurementEvent,
    ObservableSchema,
    ChannelConfig,
    IntrospectionSummary,
)


@dataclass
class MeasurementFabricState:
    """In-memory state for the measurement fabric.

    This is a minimal, runtime reflection of the Measurement Fabric
    Simulation specification: it tracks schemas, channel bindings,
    a sliding buffer of recent events, and simple introspection
    summaries.
    """

    schemas: Dict[str, ObservableSchema] = field(default_factory=dict)
    channels: Dict[str, ChannelConfig] = field(default_factory=dict)
    buffer: List[MeasurementEvent] = field(default_factory=list)
    summaries: Dict[str, IntrospectionSummary] = field(
        default_factory=dict
    )
    buffer_limit: int = 1024


class MeasurementFabric:
    """Runtime measurement fabric service.

    This service does not expose HTTP endpoints directly; it is
    intended to be called from handlers/runbooks and wired into
    the FastAPI layer by composition.
    """

    def __init__(self, state: Optional[MeasurementFabricState] = None):
        self._state = state or MeasurementFabricState()

    # --- Schema & channel management -------------------------------------------------

    def register_schema(self, schema: ObservableSchema) -> None:
        """Register or update an observable schema."""
        self._state.schemas[schema.name] = schema

    def register_channel(self, config: ChannelConfig) -> None:
        """Register or update a channel configuration."""
        if config.schema_name not in self._state.schemas:
            raise ValueError(f"Unknown schema: {config.schema_name}")
        self._state.channels[config.channel] = config

    def get_schema(self, name: str) -> Optional[ObservableSchema]:
        return self._state.schemas.get(name)

    def get_channel(self, channel: str) -> Optional[ChannelConfig]:
        return self._state.channels.get(channel)

    # --- Ingestion & buffer ---------------------------------------------------------

    def ingest(self, event: MeasurementEvent) -> None:
        """Ingest a measurement event into the fabric.

        Validates that the channel has a registered schema, then
        appends to the buffer and updates introspection summaries.
        """
        channel_cfg = self._state.channels.get(event.channel)
        if channel_cfg is None:
            raise ValueError(f"Unregistered channel: {event.channel}")

        schema = self._state.schemas.get(channel_cfg.schema_name)
        if schema is None:
            raise ValueError(
                f"Channel '{event.channel}' references unknown schema '{channel_cfg.schema_name}'"
            )

        # Enforce simple bound invariants from the measurement specification.
        value = event.value
        if isinstance(value, (int, float)):
            if schema.lower_bound is not None and value < schema.lower_bound:
                value = schema.lower_bound
            if schema.upper_bound is not None and value > schema.upper_bound:
                value = schema.upper_bound

        normalized_event = MeasurementEvent(
            channel=event.channel,
            value=value,
            ts=event.ts,
            metadata=event.metadata,
        )

        self._state.buffer.append(normalized_event)
        if len(self._state.buffer) > self._state.buffer_limit:
            self._state.buffer.pop(0)

        self._update_summary(normalized_event)

    def _update_summary(self, event: MeasurementEvent) -> None:
        summary = self._state.summaries.get(event.channel)
        if summary is None:
            summary = IntrospectionSummary(channel=event.channel)
            self._state.summaries[event.channel] = summary

        summary.count += 1
        summary.last_ts = event.ts

        aggregates = dict(summary.aggregates)
        if isinstance(event.value, (int, float)):
            count = aggregates.get("count", 0) + 1
            total = aggregates.get("total", 0.0) + float(event.value)
            aggregates["count"] = count
            aggregates["total"] = total
            aggregates["mean"] = total / count

        summary.aggregates = aggregates

    # --- Query helpers --------------------------------------------------------------

    def list_channels(self) -> List[ChannelConfig]:
        return list(self._state.channels.values())

    def list_schemas(self) -> List[ObservableSchema]:
        return list(self._state.schemas.values())

    def get_recent_events(self, channel: Optional[str] = None) -> List[MeasurementEvent]:
        if channel is None:
            return list(self._state.buffer)
        return [e for e in self._state.buffer if e.channel == channel]

    def get_summary(self, channel: str) -> Optional[IntrospectionSummary]:
        return self._state.summaries.get(channel)
