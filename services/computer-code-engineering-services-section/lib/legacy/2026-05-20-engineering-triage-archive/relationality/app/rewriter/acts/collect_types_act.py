from __future__ import annotations

from datetime import datetime

from app.schemas.fibers.payloads.type_family import TypeFamilyPayload
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class CollectTypesHandler(ActHandler):
    """Per-act handler for ``collect-types``.

    Aliases the output of construct-types as a named family of types.

    Inputs:
      - constructed_types: dict (required) – payload from construct-types.
    """

    acts = ["collect-types"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        constructed = context.get_input("constructed_types")
        if constructed is None:
            return HandlerResult.fail("Missing required input: constructed_types")

        now = datetime.utcnow().isoformat()

        payload = TypeFamilyPayload(
            types=constructed.get("types", []),
        )

        collected = constructed.copy()
        collected["act"] = act
        collected["acts"] = [act]
        collected["title"] = "Collected types"
        collected["types"] = payload.types  # already dicts/TypeASTs
        collected["collected_at"] = now

        persisted_id = await context.persist_recognition(collected)

        return HandlerResult.ok(
            outputs={"collected_types": collected},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
