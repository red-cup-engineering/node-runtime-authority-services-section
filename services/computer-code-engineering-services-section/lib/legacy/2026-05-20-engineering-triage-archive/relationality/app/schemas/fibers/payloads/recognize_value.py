from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class RecognizeValuePayload(RecognitionPayload):
    """Payload for the ``recognize-value`` act.

    Records a value recognized from a value seed, reflecting
    `(TailTrace SeedValue)`.
    """

    observation_id: Optional[str] = Field(
        default=None,
        description="Identifier of the source value observation, if known",
    )
    value: Any = Field(
        default=None,
        description="Recognized value associated with the observation",
    )

