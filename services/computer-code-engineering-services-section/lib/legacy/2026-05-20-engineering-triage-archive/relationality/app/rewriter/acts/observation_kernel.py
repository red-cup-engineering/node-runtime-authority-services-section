from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ObservationKernelHandler(ActHandler):
    """Per-act handler for ``observation-kernel``.

    This act packages a one-step transition law together with fixed
    observation recognitions into a kernel-like structure.

    Inputs:
      - states: list[dict] (required) – fixed invariant state recognitions
      - transition_law: dict (required) – mapping describing successor
        probabilities or weights between states
    """

    acts = ["observation-kernel"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        states: List[Dict[str, Any]] = context.get_input("states", [])
        transition_law: Dict[str, Any] = context.get_input("transition_law", {})

        if not states:
            return HandlerResult.fail("Missing required input: states")
        if not transition_law:
            return HandlerResult.fail("Missing required input: transition_law")

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        kernel = {
            "id": str(uuid4()),
            "type": "observation_kernel",
            "act": act,
            "acts": [act],
            "states": states,
            "transition_law": transition_law,
            "constructed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(kernel)

        return HandlerResult.ok(
            outputs={
                "kernel": kernel,
                "kernel_id": kernel["id"],
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

