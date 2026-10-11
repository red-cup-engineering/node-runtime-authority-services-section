from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.tower import ProfileTower


class ProfileKernelChainHandler(ActHandler):
    """Per-act handler for ``profile-kernel-chain``.

    Summarises how an observation kernel has been threaded through
    a profile tower by collecting kernel witnesses across levels.

    Inputs:
      - tower: dict (required) – ProfileTower payload
      - kernel: dict (required) – observation kernel payload
    """

    acts = ["profile-kernel-chain"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        tower_in = context.get_input("tower")
        kernel = context.get_input("kernel")

        if tower_in is None:
            return HandlerResult.fail("Missing required input: tower")
        if kernel is None:
            return HandlerResult.fail("Missing required input: kernel")

        try:
            tower = ProfileTower.model_validate(tower_in)
        except Exception as e:
            return HandlerResult.fail(f"Invalid profile tower payload: {e}")

        kernel_id = kernel.get("id")

        levels_with_kernel: List[int] = []
        for lvl in tower.levels:
            for w in lvl.witnesses:
                if isinstance(w, dict) and w.get("kernel_id") == kernel_id:
                    levels_with_kernel.append(lvl.level)
                    break

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        chain_recognition = {
            "id": str(uuid4()),
            "type": "profile_kernel_chain",
            "title": "Profile kernel chain",
            "act": act,
            "acts": [act],
            "tower_id": tower.id,
            "kernel_id": kernel_id,
            "levels": sorted(levels_with_kernel),
            "height": tower.height,
            "computed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(chain_recognition)

        return HandlerResult.ok(
            outputs={
                "chain": chain_recognition,
                "profile_kernel_chain": chain_recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

