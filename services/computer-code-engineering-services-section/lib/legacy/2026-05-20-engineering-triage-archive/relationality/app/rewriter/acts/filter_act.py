from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.policy import FilterRule, PolicyScope


class FilterActHandler(ActHandler):
    """Per-act handler for ``filter``.

    Constructs a FilterRule representing a content filter compatible
    with the discipline and flow.

    Inputs:
      - id: str (optional)
      - name: str (required)
      - description: str (optional)
      - match_path: str (optional, default \"*\")
      - action: str (optional, default \"mask\")
      - parameters: dict (optional)
      - applies_to_scope: str (optional, default \"recognition\")
    """

    acts = ["filter"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        name = context.get_input("name")
        if not name:
            return HandlerResult.fail("Missing required input: name")

        rule_id = context.get_input("id") or name.replace(" ", "-").lower()
        description = context.get_input("description")
        match_path = context.get_input("match_path", "*")
        action = context.get_input("action", "mask")
        parameters: Dict[str, Any] = context.get_input("parameters", {}) or {}
        scope_str = context.get_input("applies_to_scope", "recognition")

        try:
            applies_to_scope = PolicyScope(scope_str)
        except ValueError:
            applies_to_scope = PolicyScope.RECOGNITION

        rule_data: Dict[str, Any] = {
            "id": rule_id,
            "name": name,
            "description": description,
            "match_path": match_path,
            "action": action,
            "parameters": parameters,
            "applies_to_scope": applies_to_scope,
        }

        rule = FilterRule.model_validate(rule_data)

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition = {
            "id": str(uuid4()),
            "type": "filter",
            "title": f"Filter: {name}",
            "act": act,
            "acts": [act],
            "rule": rule.model_dump(mode="json"),
            "constructed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "filter": rule.model_dump(mode="json"),
                "filter_rule": rule.model_dump(mode="json"),
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
