from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class BuildReducibleEnvironmentHandler(ActHandler):
    """Per-act handler for ``build-reducible-environment``.

    Builds a reducible environment by associating variables in a typing
    context with reducible term candidates.

    Inputs:
      - context: list[dict] (required) – typing context entries, each with:
          - var: str
          - type: any
      - candidates: dict (required) – mapping from var -> reducible term data.
    """

    acts = ["build-reducible-environment"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        ctx_entries: List[Dict[str, Any]] | None = context.get_input("context")
        candidates: Dict[str, Any] | None = context.get_input("candidates")

        if not ctx_entries:
            return HandlerResult.fail("Missing required input: context")
        if candidates is None:
            return HandlerResult.fail("Missing required input: candidates")

        env: Dict[str, Any] = {}
        for entry in ctx_entries:
            var = entry.get("var")
            if not var:
                continue
            candidate = candidates.get(var)
            if candidate is None:
                continue
            env[var] = {
                "term": candidate,
                "type": entry.get("type"),
                "reducible": True,
            }

        now = datetime.utcnow().isoformat()
        reducible_env = {
            "id": str(uuid4()),
            "type": "reducible_environment",
            "title": "Reducible environment",
            "act": act,
            "acts": [act],
            "environment": env,
            "constructed_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(reducible_env)

        return HandlerResult.ok(
            outputs={
                "environment": env,
                "reducible_environment": reducible_env,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "size": len(env)},
        )

