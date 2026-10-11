from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class RecognitionRef(BaseModel):
    """Typed reference to a recognition fibre or tracepoint.

    This is used inside payloads when the math is about relations
    between recognitions, without re-embedding the full payloads.
    """

    id: str = Field(..., description="Identifier of the referenced recognition")
    acts: Optional[List[str]] = Field(
        default=None,
        description="Act footprint of the referenced recognition, if known",
    )

