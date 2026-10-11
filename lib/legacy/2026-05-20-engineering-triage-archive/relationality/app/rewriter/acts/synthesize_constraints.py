from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.topology import Constraint, ConstraintBundle, StratumEntry


class SynthesizeConstraintsHandler(ActHandler):
    """Topology integration helper (not a core act).

    Synthesises simple ordering/placement constraints from strata
    entries, as described in the topology integration specification.

    Inputs:
      - strata: list[dict] (required) – StratumEntry-like payloads
    """

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        strata_in = context.get_input("strata", [])
        if not isinstance(strata_in, list) or not strata_in:
            return HandlerResult.fail("Missing required input: strata")

        strata: List[StratumEntry] = []
        for s in strata_in:
            if not isinstance(s, dict):
                continue
            strata.append(StratumEntry.model_validate(s))

        if not strata:
            return HandlerResult.fail("No valid strata entries found")

        # Order strata by tower_level to emit ordering constraints.
        sorted_strata = sorted(strata, key=lambda e: e.tower_level)

        constraints: List[Constraint] = []

        # Ordering constraints: module at level i must execute before module at level j>i.
        for i in range(len(sorted_strata) - 1):
            a = sorted_strata[i]
            b = sorted_strata[i + 1]
            constraints.append(
                Constraint(
                    kind="ordering",
                    subject=a.module_id,
                    target=b.module_id,
                    metadata={
                        "reason": "tower_level",
                        "subject_level": a.tower_level,
                        "target_level": b.tower_level,
                    },
                )
            )

        # Placement/locality constraints based on shared coverage.region, if present.
        by_region: Dict[str, List[StratumEntry]] = {}
        for s in strata:
            region = s.coverage.get("region")
            if region:
                by_region.setdefault(str(region), []).append(s)

        for region, entries in by_region.items():
            if len(entries) < 2:
                continue
            # Locality constraints: all modules in the same region should be colocated.
            base = entries[0]
            for other in entries[1:]:
                constraints.append(
                    Constraint(
                        kind="locality",
                        subject=base.module_id,
                        target=other.module_id,
                        metadata={
                            "reason": "region",
                            "region": region,
                        },
                    )
                )

        bundle = ConstraintBundle(
            constraints=constraints,
            metadata={},
        )

        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)

        recognition = {
            "id": str(uuid4()),
            "type": "topology_constraints",
            "title": "Topology integration constraints",
            "act": act,
            "acts": [act],
            "bundle": bundle.model_dump(mode="json"),
            "constraint_count": len(constraints),
            "constructed_at": now,
            "trace_id": trace_id,
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "constraints": bundle.model_dump(mode="json"),
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "constraint_count": len(constraints)},
        )
