"""Python rewriter engine that executes runbook steps mapped to acts.

The rewriter translates runbook steps into concrete operations,
tracking provenance back to the mathematical acts that justify them.
"""

from app.rewriter.engine import (
    RewriterEngine,
    StepResult,
    ExecutionContext,
)
from app.rewriter.handlers import (
    ActHandler,
    HandlerRegistry,
    register_handler,
)

__all__ = [
    "RewriterEngine",
    "StepResult",
    "ExecutionContext",
    "ActHandler",
    "HandlerRegistry",
    "register_handler",
]
