from __future__ import annotations

from uuid import uuid4

from app.policy.engine import get_policy_engine
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.policy import (
    DisciplineRule,
    FilterRule,
    PolicyDefinition,
    PolicyScope,
)


class GovernRegimeHandler(ActHandler):
    """Handler for the ``govern-regime`` act.

    This act materialises a policy regime in the runtime by
    constructing a ``PolicyDefinition`` from discipline/filter
    descriptions and registering it with the policy engine.

    Inputs:
      - policy_id: str (required)
      - name: str (required)
      - description: str (optional)
      - scope: str (optional, defaults to \"recognition\")
      - disciplines: list[dict] (optional)
      - filters: list[dict] (optional)
    """

    acts = ["govern-regime"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        policy_id = context.get_input("policy_id")
        name = context.get_input("name")

        if not policy_id:
            return HandlerResult.fail("Missing required input: policy_id")
        if not name:
            return HandlerResult.fail("Missing required input: name")

        description = context.get_input("description")
        scope_str = context.get_input("scope", "recognition")
        disciplines_data = context.get_input("disciplines", []) or []
        filters_data = context.get_input("filters", []) or []

        try:
            scope = PolicyScope(scope_str)
        except ValueError:
            scope = PolicyScope.RECOGNITION

        disciplines: list[DisciplineRule] = []
        for d in disciplines_data:
            # Allow minimal shorthand: if only id/name provided, fill defaults.
            if "id" not in d:
                d = {**d, "id": d.get("name", f"rule-{uuid4().hex[:8]}")}
            disciplines.append(DisciplineRule.model_validate(d))

        filters: list[FilterRule] = []
        for f in filters_data:
            if "id" not in f:
                f = {**f, "id": f.get("name", f"filter-{uuid4().hex[:8]}")}
            filters.append(FilterRule.model_validate(f))

        policy = PolicyDefinition(
            id=policy_id,
            name=name,
            description=description,
            scope=scope,
            disciplines=disciplines,
            filters=filters,
        )

        engine = get_policy_engine()
        engine.register_policy(policy)

        recognition = {
            "id": str(uuid4()),
            "type": "policy_regime",
            "act": act,
            "acts": [act],
            "policy": policy.model_dump(mode="json"),
            "tags": ["policy", "regime"],
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "policy": policy.model_dump(mode="json"),
                "policy_id": policy.id,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

