from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class HarmonicModeHandler(ActHandler):
    """Per-act handler for ``harmonic-mode``.

    Approximates a harmonic mode (eigenvector) of an observation kernel
    via a simple power iteration.

    Inputs:
      - kernel: dict (required) – observation kernel with ``transition_law``
      - initial_mode: dict[str, float] (optional) – initial vector over states
      - max_steps: int (optional, default 128)
      - tolerance: float (optional, default 1e-6)
    """

    acts = ["harmonic-mode"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        kernel = context.get_input("kernel")
        if kernel is None:
            return HandlerResult.fail("Missing required input: kernel")

        transition_law: Dict[str, Dict[str, float]] = kernel.get("transition_law", {})
        if not transition_law:
            return HandlerResult.fail("Kernel missing 'transition_law'")

        initial = context.get_input("initial_mode")
        max_steps = int(context.get_input("max_steps", 128))
        tolerance = float(context.get_input("tolerance", 1e-6))

        states = sorted(
            set(transition_law.keys())
            | {s for row in transition_law.values() for s in row.keys()}
        )
        if not states:
            return HandlerResult.fail("Kernel has no states in transition_law")

        # Default initial mode: uniform vector.
        if not isinstance(initial, dict) or not initial:
            weight = 1.0 / len(states)
            mode: Dict[str, float] = {s: weight for s in states}
        else:
            mode = {s: float(initial.get(s, 0.0)) for s in states}

        history: List[Dict[str, float]] = [dict(mode)]

        def matvec(vec: Dict[str, float]) -> Dict[str, float]:
            """Compute K * vec, treating transition_law as row-stochastic."""
            result: Dict[str, float] = {s: 0.0 for s in states}
            for i in states:
                row = transition_law.get(i, {})
                vi = float(vec.get(i, 0.0))
                if vi == 0.0:
                    continue
                for j, p in row.items():
                    if j not in result:
                        continue
                    result[j] += vi * float(p)
            return result

        def l2(vec: Dict[str, float]) -> float:
            return sum(float(v) ** 2 for v in vec.values()) ** 0.5

        def normalize(vec: Dict[str, float]) -> Dict[str, float]:
            norm = l2(vec)
            if norm <= 0.0:
                return {s: 0.0 for s in states}
            return {s: float(vec.get(s, 0.0)) / norm for s in states}

        def diff(a: Dict[str, float], b: Dict[str, float]) -> float:
            return sum(abs(float(a.get(s, 0.0)) - float(b.get(s, 0.0))) for s in states)

        current = normalize(mode)
        eigenvalue = 0.0

        for _ in range(max_steps):
            next_vec = matvec(current)
            # Rayleigh quotient λ ≈ (v^T (K v)) / (v^T v)
            kv = next_vec
            numerator = sum(current[s] * kv.get(s, 0.0) for s in states)
            denominator = sum(current[s] * current[s] for s in states) or 1.0
            eigenvalue = numerator / denominator

            next_normed = normalize(next_vec)
            history.append(dict(next_normed))
            if diff(next_normed, current) < tolerance:
                current = next_normed
                break
            current = next_normed

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        mode_recognition = {
            "id": str(uuid4()),
            "type": "harmonic_mode",
            "title": "Harmonic mode approximation",
            "act": act,
            "acts": [act],
            "kernel_id": kernel.get("id"),
            "mode": current,
            "eigenvalue": eigenvalue,
            "history": history,
            "computed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(mode_recognition)

        return HandlerResult.ok(
            outputs={
                "mode": current,
                "eigenvalue": eigenvalue,
                "harmonic_mode": mode_recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

