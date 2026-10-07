from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class ReduceHandler(ActHandler):
    """Per-act handler for ``reduce``.

    Records a single beta-reduction step by forming the corresponding
    substitution step. Conceptually, this witnesses the passage from
    application terms to substitution terms.

    Inputs:
      - application: dict (required) – application term, expected to contain:
          - func: any – function part,
          - arg: any – argument part.
      - environment: dict (optional) – substitution environment to be threaded.
    """

    acts = ["reduce"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        app: Dict[str, Any] | None = context.get_input("application")
        if not app:
            return HandlerResult.fail("Missing required input: application")

        func = app.get("func")
        arg = app.get("arg")
        if func is None or arg is None:
            return HandlerResult.fail("Application is missing 'func' or 'arg'")

        env = context.get_input("environment", {}) or {}
        now = datetime.utcnow().isoformat()

        substitution_step = {
            "id": str(uuid4()),
            "type": "reduction_step",
            "act": act,
            "application": app,
            "operation": "beta-reduce",
            "term": {
                "kind": "app",
                "func": func,
                "arg": arg,
            },
            "env": env,
            "reduced_at": now,
            "trace_id": str(context.trace_id),
        }

        # In a larger runbook, this step can feed directly into
        # `substitution-term` to materialise a substitution term recognition.

        return HandlerResult.ok(
            outputs={
                "step": substitution_step,
                "term": substitution_step["term"],
                "environment": env,
            },
            metadata={"act": act},
        )

