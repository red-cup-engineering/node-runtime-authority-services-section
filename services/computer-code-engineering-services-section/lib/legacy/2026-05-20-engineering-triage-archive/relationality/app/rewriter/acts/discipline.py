from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.policy import DisciplineRule


class DisciplineHandler(ActHandler):
    """Per-act handler for ``discipline``.

    Constructs a DisciplineRule from flow/nucleus-compatible metadata.

    Inputs:
      - id: str (optional) – rule identifier; defaults from name
      - name: str (required)
      - description: str (optional)
      - match_tags: list[str] (optional)
      - match_acts: list[str] (optional)
      - match_types: list[str] (optional)
      - effect: str (optional, default \"allow\")
      - priority: int (optional, default 100)
    """

    acts = ["discipline"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        name = context.get_input("name")
        if not name:
            return HandlerResult.fail("Missing required input: name")

        rule_id = context.get_input("id") or name.replace(" ", "-").lower()
        description = context.get_input("description")
        match_tags: List[str] = context.get_input("match_tags", []) or []
        match_acts: List[str] = context.get_input("match_acts", []) or []
        match_types: List[str] = context.get_input("match_types", []) or []
        effect = context.get_input("effect", "allow")
        priority = context.get_input("priority", 100)

        rule_data: Dict[str, Any] = {
            "id": rule_id,
            "name": name,
            "description": description,
            "match_tags": match_tags,
            "match_acts": match_acts,
            "match_types": match_types,
            "effect": effect,
            "priority": priority,
        }

        rule = DisciplineRule.model_validate(rule_data)

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition = {
            "id": str(uuid4()),
            "type": "discipline",
            "title": f"Discipline: {name}",
            "act": act,
            "acts": [act],
            "rule": rule.model_dump(mode="json"),
            "constructed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "discipline": rule.model_dump(mode="json"),
                "discipline_rule": rule.model_dump(mode="json"),
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

