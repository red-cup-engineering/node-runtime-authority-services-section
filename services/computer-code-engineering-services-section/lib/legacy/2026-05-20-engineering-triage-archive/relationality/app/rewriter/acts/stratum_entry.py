from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.topology import StratumEntry


class StratumEntryHandler(ActHandler):
    """Topology integration helper (not a core act).

    Constructs one or more StratumEntry records from module/tower
    metadata. This is a helper for the strata/tower catalog in the
    topology integration specification.

    Inputs (single entry mode):
      - module_id: str
      - tower_level: int
      - coverage: dict (optional)
      - witnesses: dict (optional)

    Inputs (batch mode):
      - entries: list[dict] – each with module_id, tower_level, optional coverage/witnesses
    """

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        entries_in = context.get_input("entries")

        stratum_entries: List[StratumEntry] = []

        if isinstance(entries_in, list) and entries_in:
            for e in entries_in:
                if not isinstance(e, dict):
                    continue
                data: Dict[str, Any] = {
                    "module_id": e.get("module_id"),
                    "tower_level": e.get("tower_level"),
                    "coverage": e.get("coverage", {}) or {},
                    "witnesses": e.get("witnesses", {}) or {},
                }
                stratum_entries.append(StratumEntry.model_validate(data))
        else:
            module_id = context.get_input("module_id")
            tower_level = context.get_input("tower_level")
            if not module_id:
                return HandlerResult.fail("Missing required input: module_id")
            if tower_level is None:
                return HandlerResult.fail("Missing required input: tower_level")
            data = {
                "module_id": module_id,
                "tower_level": tower_level,
                "coverage": context.get_input("coverage", {}) or {},
                "witnesses": context.get_input("witnesses", {}) or {},
            }
            stratum_entries.append(StratumEntry.model_validate(data))

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition = {
            "id": str(uuid4()),
            "type": "strata_catalog",
            "title": "Strata/tower catalog entries",
            "act": act,
            "acts": [act],
            "entries": [e.model_dump(mode="json") for e in stratum_entries],
            "constructed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "strata": recognition["entries"],
                "strata_count": len(stratum_entries),
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "strata_count": len(stratum_entries)},
        )
