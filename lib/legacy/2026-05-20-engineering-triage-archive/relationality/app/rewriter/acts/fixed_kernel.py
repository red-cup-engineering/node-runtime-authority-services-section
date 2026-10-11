from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class FixedKernelHandler(ActHandler):
    """Per-act handler for ``fixed-kernel``.

    Approximates a stationary kernel by iterating the observation
    kernel until the state distribution stabilises.

    Inputs:
      - kernel: dict (required) – observation kernel recognition
      - initial_distribution: dict[str, float] (optional)
      - max_steps: int (optional, default 128)
      - tolerance: float (optional, default 1e-6)
    """

    acts = ["fixed-kernel"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        kernel = context.get_input("kernel")
        if kernel is None:
            return HandlerResult.fail("Missing required input: kernel")

        transition_law: Dict[str, Dict[str, float]] = kernel.get("transition_law", {})
        if not transition_law:
            return HandlerResult.fail("Kernel missing 'transition_law'")

        initial = context.get_input("initial_distribution")
        max_steps = context.get_input("max_steps", 128)
        tolerance = context.get_input("tolerance", 1e-6)

        states = list(transition_law.keys())
        if not states:
            return HandlerResult.fail("Kernel has no states in transition_law")

        # Default to uniform initial distribution if none provided.
        if not isinstance(initial, dict) or not initial:
            weight = 1.0 / len(states)
            distribution: Dict[str, float] = {s: weight for s in states}
        else:
            distribution = {s: float(initial.get(s, 0.0)) for s in states}

        history: List[Dict[str, float]] = [dict(distribution)]

        def step(dist: Dict[str, float]) -> Dict[str, float]:
            next_dist: Dict[str, float] = {s: 0.0 for s in states}
            for i in states:
                row = transition_law.get(i, {})
                for j, p in row.items():
                    if j not in next_dist:
                        continue
                    next_dist[j] += dist.get(i, 0.0) * float(p)
            total = sum(next_dist.values())
            if total > 0.0:
                for k in next_dist:
                    next_dist[k] /= total
            return next_dist

        def l1(a: Dict[str, float], b: Dict[str, float]) -> float:
            return sum(abs(a.get(s, 0.0) - b.get(s, 0.0)) for s in states)

        stationary = dict(distribution)
        for _ in range(int(max_steps)):
            next_dist = step(stationary)
            history.append(dict(next_dist))
            if l1(next_dist, stationary) < float(tolerance):
                stationary = next_dist
                break
            stationary = next_dist

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        fixed_kernel = {
            "id": str(uuid4()),
            "type": "fixed_kernel",
            "act": act,
            "acts": [act],
            "kernel_id": kernel.get("id"),
            "stationary_distribution": stationary,
            "history": history,
            "computed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(fixed_kernel)

        return HandlerResult.ok(
            outputs={
                "fixed_kernel": fixed_kernel,
                "stationary_distribution": stationary,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

