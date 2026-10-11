from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.tower import CompositeProfileTower


class BuildCompositeProfileTowerHandler(ActHandler):
    """Per-act handler for ``build-composite-profile-tower``."""

    acts = ["build-composite-profile-tower"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        towers_raw = context.get_input("towers", [])
        composition_type = context.get_input("composition_type", "sequential")

        towers: List[Dict[str, Any]] = [t for t in towers_raw if isinstance(t, dict)]

        composite = CompositeProfileTower(
            id=str(uuid4()),
            component_tower_ids=[t.get("id") for t in towers],
            composition_type=composition_type,
            component_count=len(towers_raw),
            metadata={"trace_id": trace_id, "built_at": now},
        )

        persisted_id = await context.persist_recognition(
            {
                "id": composite.id,
                "type": "composite_profile_tower",
                "act": act,
                "acts": [act],
                "tower": composite.model_dump(),
                "trace_id": trace_id,
                "built_at": now,
            }
        )

        return HandlerResult.ok(
            outputs={
                "composite_tower": composite.model_dump(),
                "tower_id": composite.id,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "component_count": len(towers_raw)},
        )
