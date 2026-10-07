from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class FixedChainHandler(ActHandler):
    """Per-act handler for ``fixed-chain``.

    Records a stationary profile-level chain by wrapping a
    profile_kernel_chain recognition and marking it as fixed.

    Inputs:
      - chain: dict (required) – profile_kernel_chain payload
    """

    acts = ["fixed-chain"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        chain = context.get_input("chain")
        if chain is None or not isinstance(chain, dict):
            return HandlerResult.fail("Missing required input: chain")

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        fixed_chain = {
            "id": str(uuid4()),
            "type": "fixed_chain",
            "title": "Fixed profile kernel chain",
            "act": act,
            "acts": [act],
            "chain": chain,
            "tower_id": chain.get("tower_id"),
            "kernel_id": chain.get("kernel_id"),
            "height": chain.get("height"),
            "levels": chain.get("levels"),
            "fixed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(fixed_chain)

        return HandlerResult.ok(
            outputs={
                "fixed_chain": fixed_chain,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

