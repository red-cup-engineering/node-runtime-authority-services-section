from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.tower import ProfileTower, ProfileLevel


class ProfileKernelStepHandler(ActHandler):
    """Per-act handler for ``profile-kernel-step``.

    Lifts an observation kernel one step along a profile tower by
    attaching kernel metadata to the corresponding tower level.

    Inputs:
      - tower: dict (required) – ProfileTower payload
      - level: int (required) – tower level index
      - kernel: dict (required) – observation kernel payload
    """

    acts = ["profile-kernel-step"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        tower_in = context.get_input("tower")
        level = context.get_input("level")
        kernel = context.get_input("kernel")

        if tower_in is None:
            return HandlerResult.fail("Missing required input: tower")
        if level is None:
            return HandlerResult.fail("Missing required input: level")
        if kernel is None:
            return HandlerResult.fail("Missing required input: kernel")

        try:
            tower = ProfileTower.model_validate(tower_in)
        except Exception as e:
            return HandlerResult.fail(f"Invalid profile tower payload: {e}")

        try:
            level_idx = int(level)
        except Exception:
            return HandlerResult.fail("Input 'level' must be an integer")

        if level_idx < 0 or level_idx >= tower.height:
            return HandlerResult.fail(
                f"Level index {level_idx} out of range for tower height {tower.height}"
            )

        levels: List[ProfileLevel] = list(tower.levels)
        lvl = levels[level_idx]

        witnesses = list(lvl.witnesses)
        witnesses.append(
            {
                "act": act,
                "kernel_id": kernel.get("id"),
                "transition_law": kernel.get("transition_law"),
            }
        )
        levels[level_idx] = ProfileLevel(
            level=lvl.level,
            profile=lvl.profile,
            witnesses=witnesses,
        )

        updated_tower = ProfileTower(
            id=tower.id,
            base_profile=tower.base_profile,
            height=tower.height,
            levels=levels,
            metadata=dict(tower.metadata),
        )

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition = {
            "id": str(uuid4()),
            "type": "profile_kernel_step",
            "title": "Profile kernel step",
            "act": act,
            "acts": [act],
            "tower_id": updated_tower.id,
            "level": level_idx,
            "kernel_id": kernel.get("id"),
            "applied_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "tower": updated_tower.model_dump(),
                "profile_kernel_step": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "level": level_idx},
        )

