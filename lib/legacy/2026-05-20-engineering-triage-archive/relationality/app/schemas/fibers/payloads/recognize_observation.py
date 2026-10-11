from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class RecognizeObservationPayload(RecognitionPayload):
    """Payload for the ``recognize-observation`` act.

    Records a value recognized from an observation seed, reflecting
    `(TailTrace SeedObservation)`.
    """

    observation_id: Optional[str] = Field(
        default=None,
        description="Identifier of the source observation, if known",
    )
    value: Any = Field(
        default=None,
        description="Recognized value associated with the observation",
    )

