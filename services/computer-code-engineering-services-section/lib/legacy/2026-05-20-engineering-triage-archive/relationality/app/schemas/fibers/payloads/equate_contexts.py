from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload


class EquateContextsPayload(RecognitionPayload):
    """Payload for the ``equate-contexts`` act.

    Records contextual indistinguishability data for normalized terms.

    The act itself reflects the composition `(RecognizeContext Normalization)`;
    here we store whatever identifiers or payloads the caller provides for
    the normalized witnesses.
    """

    left: Optional[Any] = Field(
        default=None,
        description="Left normalized term/observation under comparison",
    )
    right: Optional[Any] = Field(
        default=None,
        description="Right normalized term/observation under comparison",
    )
