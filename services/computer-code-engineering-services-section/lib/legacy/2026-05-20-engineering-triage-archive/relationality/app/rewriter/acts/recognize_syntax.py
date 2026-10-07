from __future__ import annotations

from datetime import datetime

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class RecognizeSyntaxHandler(ActHandler):
    """Per-act handler for ``recognize-syntax``.

    Validates a recognition against minimal structural requirements.
    """

    acts = ["recognize-syntax"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        recognition = context.get_input("recognition")
        schema = context.get_input("schema")  # currently unused, reserved hook

        if recognition is None:
            return HandlerResult.fail("Missing required input: recognition")

        is_valid = True
        errors: list[str] = []

        if not isinstance(recognition, dict):
            is_valid = False
            errors.append("Recognition must be a mapping")

        if is_valid and "type" not in recognition:
            is_valid = False
            errors.append("Recognition missing required field: type")

        if is_valid and "acts" not in recognition:
            recognition["acts"] = []

        validation_result = {
            "is_valid": is_valid,
            "errors": errors,
            "validated_at": datetime.utcnow().isoformat(),
            "act": act,
        }

        return HandlerResult.ok(
            outputs={
                "is_valid": is_valid,
                "errors": errors,
                "validation_result": validation_result,
            },
            metadata={"act": act},
        )

