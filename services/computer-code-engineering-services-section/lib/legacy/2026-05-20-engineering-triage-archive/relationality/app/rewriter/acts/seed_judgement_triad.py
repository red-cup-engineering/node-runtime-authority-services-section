from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SeedJudgementTriadHandler(ActHandler):
    """Per-act handler for ``seed-judgement-triad``.

    This act packages a single judgement triad:
      - typing context
      - term
      - observation / normal form
    into one recognition, matching the Seed Judgement Triad act.

    Inputs
    ------
    context: dict
        Typing context / environment.
    term: dict
        Term AST or equivalent structure.
    observation: dict
        Observation / normal form structure.
    """

    acts = ["seed-judgement-triad"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        typing_context = context.get_input("context")
        term = context.get_input("term")
        observation = context.get_input("observation")

        if typing_context is None or term is None or observation is None:
            return HandlerResult.fail(
                "Missing required inputs: context, term, observation"
            )

        triad_id = uuid4()
        now = datetime.utcnow().isoformat()

        triad = {
            "id": str(triad_id),
            "type": "judgement_triad",
            "title": "Seeded judgement triad",
            "act": act,
            "acts": [act],
            "context": typing_context,
            "term": term,
            "observation": observation,
            "seeded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(triad)

        return HandlerResult.ok(
            outputs={"triad": triad, "triad_id": str(persisted_id)},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

