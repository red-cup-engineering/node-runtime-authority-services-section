from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.tower import NestedProfileTower


class BuildNestedProfileTowerHandler(ActHandler):
    """Per-act handler for ``build-nested-profile-tower``."""

    acts = ["build-nested-profile-tower"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        outer_tower = context.get_input("outer_tower")
        inner_profile = context.get_input("inner_profile", {})
        nesting_level = context.get_input("nesting_level", 0)

        if not outer_tower:
            return HandlerResult.fail("Missing required input: outer_tower")

        nested = NestedProfileTower(
            id=str(uuid4()),
            outer_tower_id=outer_tower.get("id"),
            inner_profile=inner_profile,
            nesting_level=nesting_level,
            metadata={"trace_id": trace_id, "built_at": now},
        )

        persisted_id = await context.persist_recognition(
            {
                "id": nested.id,
                "type": "nested_profile_tower",
                "act": act,
                "acts": [act],
                "tower": nested.model_dump(),
                "trace_id": trace_id,
                "built_at": now,
            }
        )

        return HandlerResult.ok(
            outputs={
                "nested_tower": nested.model_dump(),
                "tower_id": nested.id,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "nesting_level": nesting_level},
        )
