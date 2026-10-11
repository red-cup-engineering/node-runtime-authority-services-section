from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.policy import DisciplineRule


class ComposeDisciplineHandler(ActHandler):
    """Per-act handler for ``compose-discipline``.

    Combines multiple DisciplineRule payloads into a composite rule
    that matches when any of the underlying disciplines match.

    Inputs:
      - disciplines: list[dict] (required) – discipline rule payloads
      - id, name, description (optional overrides)
    """

    acts = ["compose-discipline"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        disciplines_data: List[Dict[str, Any]] = context.get_input("disciplines", []) or []
        if not disciplines_data:
            return HandlerResult.fail("Missing required input: disciplines")

        base_rules: List[DisciplineRule] = [
            DisciplineRule.model_validate(d) for d in disciplines_data
        ]

        name = context.get_input("name") or "composed-discipline"
        rule_id = context.get_input("id") or name.replace(" ", "-").lower()
        description = context.get_input("description") or "Composite discipline"

        match_tags: List[str] = sorted(
            {tag for r in base_rules for tag in r.match_tags}
        )
        match_acts: List[str] = sorted(
            {a for r in base_rules for a in r.match_acts}
        )
        match_types: List[str] = sorted(
            {t for r in base_rules for t in r.match_types}
        )
        priority = max((r.priority for r in base_rules), default=100)
        effect = base_rules[0].effect if base_rules else None

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

        composite = DisciplineRule.model_validate(rule_data)

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition = {
            "id": str(uuid4()),
            "type": "discipline_composite",
            "title": f"Composite discipline: {name}",
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
                "discipline": composite.model_dump(mode="json"),
                "discipline_rule": composite.model_dump(mode="json"),
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
