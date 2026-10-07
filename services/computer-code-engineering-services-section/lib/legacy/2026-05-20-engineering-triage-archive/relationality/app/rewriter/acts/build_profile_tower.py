from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.hypertensor import LatticeSite, LatticeWindow, SheafSection
from app.schemas.tower import ProfileLevel, ProfileTower


class BuildProfileTowerHandler(ActHandler):
    """Per-act handler for ``build-profile-tower``."""

    acts = ["build-profile-tower"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        base_profile = context.get_input("base_profile", {})
        height = context.get_input("height", 1)

        levels = [
            ProfileLevel(
                level=i,
                profile={**base_profile, "level": i} if i == 0 else {},
                witnesses=[],
            )
            for i in range(height)
        ]

        tower = ProfileTower(
            id=str(uuid4()),
            fiber_id=trace_id,
            base_profile=base_profile,
            height=height,
            levels=levels,
            built_at=None,
            metadata={},
        )

        # Build a minimal sheaf section carrier over a trivial 1D window,
        # as justified by the Sheaf Sections theorem: a finite window plus a
        # finite family of towers determines a section.
        window = LatticeWindow(
            dimension=1,
            sites=[
                LatticeSite(
                    index=(0,),
                    recognition_id=tower.id,
                    metadata={"role": "tower-fibre"},
                )
            ],
            metadata={"kind": "minimal-fibre-window"},
        )
        sheaf_section = SheafSection(
            window=window,
            towers=[tower],
            metadata={
                "kind": "minimal-fibre-section",
                "trace_id": trace_id,
            },
        )

        persisted_id = await context.persist_recognition(
            {
                "id": tower.id,
                "type": "profile_tower",
                "act": act,
                "acts": [act],
                "tower": tower.model_dump(),
                "trace_id": trace_id,
                "built_at": now,
            }
        )

        return HandlerResult.ok(
            outputs={
                "tower": tower.model_dump(),
                "tower_id": tower.id,
                "sheaf_section": sheaf_section.model_dump(),
                "height": height,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "height": height},
        )
