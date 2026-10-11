from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.policy import FilterRule


class ComposeFilterActHandler(ActHandler):
    """Per-act handler for ``compose-filter``.

    Combines multiple FilterRule payloads into a composite filter by
    collecting their actions and parameters. This is a simple logical
    composition suitable for wiring into policies.

    Inputs:
      - filters: list[dict] (required)
      - id, name, description (optional overrides)
    """

    acts = ["compose-filter"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        filters_data: List[Dict[str, Any]] = context.get_input("filters", []) or []
        if not filters_data:
            return HandlerResult.fail("Missing required input: filters")

        base_rules: List[FilterRule] = [
            FilterRule.model_validate(f) for f in filters_data
        ]

        name = context.get_input("name") or "composed-filter"
        rule_id = context.get_input("id") or name.replace(" ", "-").lower()
        description = context.get_input("description") or "Composite filter"

        # For simplicity, we take the first match_path/action and merge parameters.
        match_path = base_rules[0].match_path if base_rules else "*"
        action = base_rules[0].action if base_rules else "mask"
        applies_to_scope = base_rules[0].applies_to_scope if base_rules else None
        merged_params: Dict[str, Any] = {}
        for r in base_rules:
            merged_params.update(r.parameters)

        rule_data: Dict[str, Any] = {
            "id": rule_id,
            "name": name,
            "description": description,
            "match_path": match_path,
            "action": action,
            "parameters": merged_params,
            "applies_to_scope": applies_to_scope,
        }

        composite = FilterRule.model_validate(rule_data)

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition = {
            "id": str(uuid4()),
            "type": "filter_composite",
            "title": f"Composite filter: {name}",
            "act": act,
            "acts": [act],
            "rule": composite.model_dump(mode="json"),
            "components": [r.model_dump(mode="json") for r in base_rules],
            "constructed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "filter": composite.model_dump(mode="json"),
                "filter_rule": composite.model_dump(mode="json"),
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
