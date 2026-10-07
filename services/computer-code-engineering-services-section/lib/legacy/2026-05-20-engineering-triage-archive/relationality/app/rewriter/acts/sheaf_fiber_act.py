from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.topology import SheafFiber


class SheafFiberActHandler(ActHandler):
    """Topology integration helper (not a core act).

    Constructs a SheafFiber record from object/cover/section data.

    Inputs:
      - object_id: str
      - cover_id: str
      - section_data: dict (optional)
    """

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        object_id = context.get_input("object_id")
        cover_id = context.get_input("cover_id")
        section_data = context.get_input("section_data", {}) or {}

        if not object_id:
            return HandlerResult.fail("Missing required input: object_id")
        if not cover_id:
            return HandlerResult.fail("Missing required input: cover_id")

        fiber = SheafFiber(
            object_id=str(object_id),
            cover_id=str(cover_id),
            section_data=section_data,
        )

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition = {
            "id": str(uuid4()),
            "type": "sheaf_fiber",
            "title": "Sheaf fiber / glued section",
            "act": act,
            "acts": [act],
            "fiber": fiber.model_dump(mode="json"),
            "constructed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "fiber": fiber.model_dump(mode="json"),
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
