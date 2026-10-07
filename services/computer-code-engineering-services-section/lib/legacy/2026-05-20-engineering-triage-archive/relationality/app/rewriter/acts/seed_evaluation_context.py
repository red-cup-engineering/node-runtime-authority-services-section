from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SeedEvaluationContextHandler(ActHandler):
    """Per-act handler for ``seed-evaluation-context``.

    Extracts the first evaluation frame from a trace by witnessing
    the head of a step trace. The handler:

    - reads a trace whose ``steps`` field contains reduction steps,
    - selects the first step as the initial evaluation frame,
    - records it as an ``evaluation_context`` recognition.

    Inputs:
      - trace: dict (required) – trace with a ``steps`` list.
    """

    acts = ["seed-evaluation-context"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace: Dict[str, Any] | None = context.get_input("trace")
        if not trace:
            return HandlerResult.fail("Missing required input: trace")

        steps: List[Dict[str, Any]] = list(trace.get("steps", []))
        if not steps:
            return HandlerResult.fail("Trace has no steps to seed evaluation context from")

        first_step = steps[0]
        now = datetime.utcnow().isoformat()

        evaluation_context = {
            "id": str(uuid4()),
            "type": "evaluation_context",
            "title": "Seeded evaluation context",
            "act": act,
            "acts": [act],
            "source_trace_id": trace.get("id"),
            "frame": first_step,
            "frame_position": first_step.get("position"),
            "seeded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(evaluation_context)

        return HandlerResult.ok(
            outputs={
                "evaluation_context": evaluation_context,
                "frame": first_step,
            },
            recognitions_created=[persisted_id],
            metadata={
                "act": act,
                "frame_position": first_step.get("position"),
            },
        )

