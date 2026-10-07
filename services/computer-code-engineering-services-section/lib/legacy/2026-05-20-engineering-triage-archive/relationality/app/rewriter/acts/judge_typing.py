from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List, Optional

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.stlc import TermAST, TypeAST, TypingContext, TypingContextEntry


class JudgeTypingHandler(ActHandler):
    """Per-act handler for ``judge-typing``.

    Implements a minimal, syntax-directed typing judgement
    Γ ⊢ t : A for a small STLC fragment (var, lam, app).

    This is intentionally conservative and focuses on the
    core rules; it can be extended to cover more constructs
    as the specification is elaborated.
    """

    acts = ["judge-typing"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        term_in: Dict[str, Any] = context.get_input("term")
        ctx_in: List[Dict[str, Any]] = context.get_input("context", [])

        if term_in is None:
            return HandlerResult.fail("Missing required input: term")

        try:
            term = TermAST.model_validate(term_in)
        except Exception as e:
            return HandlerResult.fail(f"Invalid term AST: {e}")

        try:
            ctx = TypingContext(
                entries=[
                    TypingContextEntry.model_validate(entry) for entry in ctx_in
                ]
            )
        except Exception as e:
            return HandlerResult.fail(f"Invalid typing context: {e}")

        ty, errors = self._judge(ctx, term)

        judgement = {
            "id": str(uuid4()),
            "type": "typing_judgement",
            "act": act,
            "acts": [act],
            "term": term.model_dump(),
            "context": ctx.model_dump(),
            "type_ast": ty.model_dump() if ty else None,
            "errors": errors,
            "judged_at": now,
            "trace_id": trace_id,
        }

        success = ty is not None and not errors

        return HandlerResult.ok(
            outputs={
                "judgement": judgement,
                "type": ty.model_dump() if ty else None,
                "ok": success,
                "errors": errors,
            },
            metadata={"act": act, "ok": success},
        )

    def _lookup(self, ctx: TypingContext, var: str) -> Optional[TypeAST]:
        for entry in reversed(ctx.entries):
            if entry.var == var:
                return entry.type
        return None

    def _judge(
        self,
        ctx: TypingContext,
        term: TermAST,
    ) -> tuple[Optional[TypeAST], List[str]]:
        """Minimal typing derivation for var/lam/app."""
        errors: List[str] = []

        if term.kind == "var":
            if not term.var:
                errors.append("Variable term missing 'var' field")
                return None, errors
            ty = self._lookup(ctx, term.var)
            if ty is None:
                errors.append(f"Unbound variable: {term.var}")
            return ty, errors

        if term.kind == "lam":
            if not term.var:
                errors.append("Lambda term missing 'var' field")
                return None, errors
            if term.type is None:
                errors.append("Lambda term missing parameter type annotation")
                return None, errors

            extended = TypingContext(
                entries=ctx.entries
                + [TypingContextEntry(var=term.var, type=term.type)]
            )
            if term.body is None:
                errors.append("Lambda term missing 'body'")
                return None, errors

            body_ty, body_errors = self._judge(extended, term.body)
            errors.extend(body_errors)
            if body_ty is None:
                return None, errors

            arrow = TypeAST(kind="arrow", left=term.type, right=body_ty)
            return arrow, errors

        if term.kind == "app":
            if term.func is None or term.arg is None:
                errors.append("Application term requires 'func' and 'arg'")
                return None, errors

            func_ty, func_errors = self._judge(ctx, term.func)
            arg_ty, arg_errors = self._judge(ctx, term.arg)
            errors.extend(func_errors)
            errors.extend(arg_errors)

            if func_ty is None or arg_ty is None:
                return None, errors

            if func_ty.kind != "arrow" or func_ty.left is None or func_ty.right is None:
                errors.append("Function position does not have arrow type")
                return None, errors

            if func_ty.left != arg_ty:
                errors.append(
                    f"Argument type {arg_ty} does not match parameter type {func_ty.left}"
                )
                return None, errors

            return func_ty.right, errors

        errors.append(f"Unsupported term kind: {term.kind}")
        return None, errors

