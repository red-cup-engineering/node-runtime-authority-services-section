from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.fibers.payloads.entry_pair import EntryPairPayload


class LeadTrailEntryPayload(RecognitionPayload):
    """Shared payload for ``lead-entry`` and ``trail-entry`` acts.

    Records the underlying entry structure together with which side is
    leading and which is trailing. Orientation is expressed in terms of
    positions, not opaque IDs.
    """

    entry: EntryPairPayload = Field(
        ..., description="Underlying entry pair structure"
    )
    leader_position: Literal["left", "right"] = Field(
        ..., description="Which entry position is treated as leader"
    )
    trailing_position: Literal["left", "right"] = Field(
        ..., description="Which entry position is treated as trailing"
    )
