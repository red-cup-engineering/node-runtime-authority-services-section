from __future__ import annotations

from datetime import datetime

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class NormalizeSyntaxHandler(ActHandler):
    """Per-act handler for ``normalize-syntax``."""

    acts = ["normalize-syntax"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        recognition = context.get_input("recognition")

        if recognition is None:
            return HandlerResult.fail("Missing required input: recognition")

        normalized = dict(recognition)

        if "acts" not in normalized:
            normalized["acts"] = [act]
        else:
            acts = list(normalized.get("acts", []))
            if act not in acts:
                acts.append(act)
            normalized["acts"] = acts

        normalized["normalized_at"] = datetime.utcnow().isoformat()

        return HandlerResult.ok(
            outputs={"normalized": normalized},
            metadata={"act": act},
        )

