from __future__ import annotations

from datetime import datetime

from app.schemas.fibers.payloads.context_family import ContextFamilyPayload
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class CollectContextsHandler(ActHandler):
    """Per-act handler for ``collect-contexts``.

    Aliases the output of construct-contexts as the explicit family of contexts.

    Inputs:
      - constructed_contexts: dict (required).
    """

    acts = ["collect-contexts"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        constructed = context.get_input("constructed_contexts")
        if constructed is None:
            return HandlerResult.fail("Missing required input: constructed_contexts")

        now = datetime.utcnow().isoformat()

        payload = ContextFamilyPayload(
            contexts=constructed.get("contexts", []),
        )

        collected = constructed.copy()
        collected["act"] = act
        collected["acts"] = [act]
        collected["title"] = "Collected contexts"
        collected["contexts"] = payload.contexts
        collected["collected_at"] = now

        persisted_id = await context.persist_recognition(collected)

        return HandlerResult.ok(
            outputs={"collected_contexts": collected},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
