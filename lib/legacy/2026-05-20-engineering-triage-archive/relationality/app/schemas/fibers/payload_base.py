from __future__ import annotations

from pydantic import BaseModel


class RecognitionPayload(BaseModel):
    """Base class for payloads carried by a recognition fibre.

    Concrete payloads (order witnesses, meet/join witnesses, term payloads,
    etc.) should inherit from this type.
    """

    pass

