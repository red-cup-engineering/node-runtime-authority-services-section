from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SubstitutionTermHandler(ActHandler):
    """Per-act handler for ``substitution-term``.

    Forms a substitution term record from a substitution step by:

    - reading a substitution *step* (e.g. from a reduction trace),
    - extracting the term being substituted and the environment,
    - recording them as a `substitution_term` recognition.

    Inputs:
      - step: dict (required) – substitution step payload, expected to contain:
          - term: any (the term after substitution),
          - env: any (substitution environment), optional.
    """

    acts = ["substitution-term"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        step: Dict[str, Any] | None = context.get_input("step")
        if not step:
            return HandlerResult.fail("Missing required input: step")

        term = step.get("term")
        if term is None:
            return HandlerResult.fail("Substitution step is missing 'term'")

        env = step.get("env", {})
        now = datetime.utcnow().isoformat()

        substitution_term = {
            "id": str(uuid4()),
            "type": "substitution_term",
            "title": "Substitution term",
            "act": act,
            "acts": [act],
            "term": term,
            "environment": env,
            "source_step": step,
            "recorded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(substitution_term)

        return HandlerResult.ok(
            outputs={
                "substitution_term": substitution_term,
                "term": term,
                "environment": env,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

