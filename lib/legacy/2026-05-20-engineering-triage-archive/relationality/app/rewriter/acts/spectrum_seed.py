from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SpectrumSeedHandler(ActHandler):
    """Per-act handler for ``spectrum-seed``.

    Records how an observation kernel acts on a harmonic mode by
    computing K * v for a given mode vector.

    Inputs:
      - kernel: dict (required)
      - mode: dict[str, float] (required)
    """

    acts = ["spectrum-seed"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        kernel = context.get_input("kernel")
        mode: Dict[str, Any] = context.get_input("mode", {})

        if kernel is None:
            return HandlerResult.fail("Missing required input: kernel")
        if not mode:
            return HandlerResult.fail("Missing required input: mode")

        transition_law: Dict[str, Dict[str, float]] = kernel.get("transition_law", {})
        if not transition_law:
            return HandlerResult.fail("Kernel missing 'transition_law'")

        states = sorted(
            set(transition_law.keys())
            | {s for row in transition_law.values() for s in row.keys()}
        )
        if not states:
            return HandlerResult.fail("Kernel has no states in transition_law")

        def matvec(vec: Dict[str, float]) -> Dict[str, float]:
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

        image = matvec({s: float(mode.get(s, 0.0)) for s in states})

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        seed_recognition = {
            "id": str(uuid4()),
            "type": "spectrum_seed",
            "title": "Spectrum seed (K * mode)",
            "act": act,
            "acts": [act],
            "kernel_id": kernel.get("id"),
            "mode": mode,
            "image": image,
            "computed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(seed_recognition)

        return HandlerResult.ok(
            outputs={
                "spectrum_seed": seed_recognition,
                "image": image,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

