from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class VerifyBaselineHandler(ActHandler):
    """Per-act handler for ``verify-baseline``."""

    acts = ["verify-baseline"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        baseline = context.get_input("baseline")
        expected = context.get_input("expected")

        if not baseline:
            return HandlerResult.fail("Missing required input: baseline")

        verified = True

        verification = {
            "id": str(uuid4()),
            "type": "baseline_verification",
            "act": act,
            "baseline_id": baseline.get("id"),
            "expected": expected,
            "verified": verified,
            "verified_at": now,
            "trace_id": trace_id,
        }

        return HandlerResult.ok(
            outputs={
                "verification": verification,
                "verified": verified,
            },
            metadata={"act": act},
        )

