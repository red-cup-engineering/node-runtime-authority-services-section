from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Tuple
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.stlc import TermAST


class EvaluateObservationHandler(ActHandler):
    """Per-act handler for ``evaluate-observation``.

    Interprets an observation payload that contains an STLC term AST and
    produces a strongly normalised value plus an evaluation trace.

    Inputs:
      - observation: dict (required) – seeded observation whose payload has
        a ``term`` field matching ``TermAST``.

    Outputs:
      - evaluation: dict – evaluation recognition with term, value, and steps
      - value: dict | None – normal form term AST, if evaluation succeeded
      - steps: list[dict] – intermediate term ASTs visited (including final)
    """

    acts = ["evaluate-observation"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        observation = context.get_input("observation")
        if observation is None:
            return HandlerResult.fail("Missing required input: observation")

        payload = observation.get("payload", {})
        term_in = payload.get("term")
        if term_in is None:
            return HandlerResult.fail("Observation payload missing 'term'")

        try:
            term = TermAST.model_validate(term_in)
        except Exception as e:
            return HandlerResult.fail(f"Invalid term AST in observation payload: {e}")

        value, steps, error = self._normalize(term)
        if error is not None:
            return HandlerResult.fail(error)

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        evaluation = {
            "id": str(uuid4()),
            "type": "judgement",
            "title": "Evaluation (observation)",
            "act": act,
            "acts": [act],
            "observation_id": observation.get("id"),
            "term": term.model_dump(),
            "value": value.model_dump() if value is not None else None,
            "steps": [t.model_dump() for t in steps],
            "evaluated_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(evaluation)

        return HandlerResult.ok(
            outputs={
                "evaluation": evaluation,
                "value": evaluation["value"],
                "steps": evaluation["steps"],
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

    def _is_value(self, term: TermAST) -> bool:
        """In this fragment, values are lambdas."""
        return term.kind == "lam"

    def _substitute(self, term: TermAST, var: str, value: TermAST) -> TermAST:
        """Capture-avoiding substitution (up to shadowing).

        This avoids substituting under binders that reuse the same variable
        name; it does not perform alpha-renaming of binders, which is
        sufficient for the small, explicit terms used in examples.
        """
        if term.kind == "var":
            if term.var == var:
                return value
            return term

        if term.kind == "lam":
            # Shadowing: do not substitute under this binder.
            if term.var == var:
                return term
            body = term.body
            new_body = self._substitute(body, var, value) if body is not None else None
            return TermAST(kind="lam", var=term.var, type=term.type, body=new_body)

        if term.kind == "app":
            func = term.func
            arg = term.arg
            new_func = self._substitute(func, var, value) if func is not None else None
            new_arg = self._substitute(arg, var, value) if arg is not None else None
            return TermAST(kind="app", func=new_func, arg=new_arg)

        return term

    def _step(self, term: TermAST) -> Optional[TermAST]:
        """One call-by-value beta-reduction step, or None if in normal form."""
        if term.kind == "app":
            func = term.func
            arg = term.arg

            if func is not None and func.kind == "lam" and arg is not None and self._is_value(arg):
                # (λx:A. t) v  ->  t[x := v]
                if func.body is None or func.var is None:
                    return None
                return self._substitute(func.body, func.var, arg)

            # Reduce function position first (call-by-value, left-to-right)
            if func is not None and not self._is_value(func):
                next_func = self._step(func)
                if next_func is not None:
                    return TermAST(kind="app", func=next_func, arg=arg)

            # Then reduce the argument
            if arg is not None and not self._is_value(arg):
                next_arg = self._step(arg)
                if next_arg is not None:
                    return TermAST(kind="app", func=func, arg=next_arg)

            return None

        if term.kind == "lam":
            # Try to reduce inside the body
            if term.body is not None:
                next_body = self._step(term.body)
                if next_body is not None:
                    return TermAST(
                        kind="lam",
                        var=term.var,
                        type=term.type,
                        body=next_body,
                    )
            return None

        # Variables and other constructors are already in normal form here.
        return None

    def _normalize(
        self,
        term: TermAST,
        max_steps: int = 1024,
    ) -> Tuple[Optional[TermAST], List[TermAST], Optional[str]]:
        """Strongly normalise a term with a simple CBV strategy.

        Returns (value, steps, error_message).
        """
        steps: List[TermAST] = [term]
        current = term
        for _ in range(max_steps):
            next_term = self._step(current)
            if next_term is None:
                return current, steps, None
            steps.append(next_term)
            current = next_term
        return None, steps, "Maximum evaluation steps exceeded; possible non-terminating term"

