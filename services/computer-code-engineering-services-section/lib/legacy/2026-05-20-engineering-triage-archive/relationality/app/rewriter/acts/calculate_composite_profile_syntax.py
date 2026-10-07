from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class CalculateCompositeProfileSyntaxHandler(ActHandler):
    """Per-act handler for ``calculate-composite-profile-syntax``."""

    acts = ["calculate-composite-profile-syntax"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()
        tower = context.get_input("tower")

        if not tower:
            return HandlerResult.fail("Missing required input: tower")

        syntax = {
            "id": str(uuid4()),
            "type": "profile_syntax",
            "act": act,
            "tower_id": tower.get("id"),
            "tower_type": tower.get("type"),
            "height": tower.get("height", 0),
            "calculated_at": now,
        }

        return HandlerResult.ok(
            outputs={"syntax": syntax},
            metadata={"act": act},
        )

