from __future__ import annotations

from datetime import datetime

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class SoundSyntaxHandler(ActHandler):
    """Per-act handler for ``sound-syntax``.

    Marks a recognition as syntactically sound once other checks have passed.
    """

    acts = ["sound-syntax"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        recognition = context.get_input("recognition")

        if recognition is None:
            return HandlerResult.fail("Missing required input: recognition")

        sound = dict(recognition)
        sound["syntactically_sound"] = True
        sound["sound_checked_at"] = datetime.utcnow().isoformat()

        return HandlerResult.ok(
            outputs={"recognition": sound},
            metadata={"act": act},
        )

