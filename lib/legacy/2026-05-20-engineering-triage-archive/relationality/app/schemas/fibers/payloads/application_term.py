from __future__ import annotations

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.stlc import TermAST


class ApplicationTermPayload(RecognitionPayload):
    """Typed payload for the ``form-application-term`` act.

    Carries a STLC application term and a tail term, matching
    `(PairApplication TailTrace)`.
    """

    application: TermAST = Field(
        ..., description="Application term (func/arg) after pairing"
    )
    tail: TermAST = Field(
        ..., description="Tail term describing the remaining body"
    )
