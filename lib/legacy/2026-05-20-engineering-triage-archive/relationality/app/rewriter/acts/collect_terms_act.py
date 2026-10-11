from __future__ import annotations

from datetime import datetime

from app.schemas.fibers.payloads.term_family import TermFamilyPayload
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class CollectTermsHandler(ActHandler):
    """Per-act handler for ``collect-terms``.

    Aliases the output of construct-terms as a catalog of terms.

    Inputs:
      - constructed_terms: dict (required) – payload from construct-terms.
    """

    acts = ["collect-terms"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        constructed = context.get_input("constructed_terms")
        if constructed is None:
            return HandlerResult.fail("Missing required input: constructed_terms")

        now = datetime.utcnow().isoformat()

        payload = TermFamilyPayload(
            terms=constructed.get("terms", []),
        )

        collected = constructed.copy()
        collected["act"] = act
        collected["acts"] = [act]
        collected["title"] = "Collected terms"
        collected["terms"] = payload.terms
        collected["collected_at"] = now

        persisted_id = await context.persist_recognition(collected)

        return HandlerResult.ok(
            outputs={"collected_terms": collected},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
