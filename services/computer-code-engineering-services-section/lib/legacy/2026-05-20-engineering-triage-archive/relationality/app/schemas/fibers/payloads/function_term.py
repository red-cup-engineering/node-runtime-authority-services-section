from __future__ import annotations

from pydantic import Field

from app.schemas.fibers.payload_base import RecognitionPayload
from app.schemas.stlc import TermAST, TypingContext


class FunctionTermPayload(RecognitionPayload):
    """Typed payload for the ``form-function-term`` act.

    Carries a STLC term body together with a typing context, matching
    the `(FormTermBody TraceContext)` shape from the act doc.
    """

    body: TermAST = Field(
        ..., description="STLC term body used to form the function term"
    )
    trace_context: TypingContext = Field(
        ..., description="Typing context paired with the body"
    )
