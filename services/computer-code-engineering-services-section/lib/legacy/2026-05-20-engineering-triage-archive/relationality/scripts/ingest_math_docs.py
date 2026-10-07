from __future__ import annotations

"""
One-shot ingestion of math markdown files as text observations.

This script walks `docs/math/content/`, reads each `.md` file, and ingests its
contents into the relational computer as a simple text observation using the
`seed-observation` act via the runbook engine.

Each file becomes a TracePoint whose `content` contains:

    {"payload": {"kind": "text", "text": "<full markdown>"}}

No source/path/URI metadata is stored; only the text itself is ingested.

Usage (from repo root):

    python scripts/ingest_math_docs.py
"""

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.rewriter.engine import RewriterEngine
from app.rewriter.handlers import HandlerRegistry
from app.schemas.runbook import RunbookCreate, RunbookStep, StepInput, StepOutput
from app.storage.database import init_db
from app.storage.repositories import RecognitionRepository


ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = ROOT / "docs" / "math" / "content"


def make_ingest_text_runbook() -> RunbookCreate:
    """Construct an in-memory runbook equivalent to ingest-text.yaml."""
    ingest_step = RunbookStep(
        id="ingest_text",
        name="Ingest text as observation",
        description="Seed a minimal text payload as an observation TracePoint",
        acts=["seed-observation"],
        depends_on=[],
        inputs=[
            StepInput(
                name="payload",
                type="any",
                required=True,
            )
        ],
        outputs=[
            StepOutput(name="observation_id", type="string"),
            StepOutput(name="observation", type="any"),
        ],
    )

    return RunbookCreate(
        name="ingest-text-batch",
        description="Batch ingest math markdown files as text observations",
        version="1.0.0",
        steps=[ingest_step],
        tags=["ingest", "text", "math-docs"],
        policy_requirements=[],
    )


async def ingest_file(
    engine: RewriterEngine,
    runbook: RunbookCreate,
    text: str,
) -> dict[str, Any]:
    """Execute the ingest-text runbook for a single text blob."""
    inputs = {"payload": {"kind": "text", "text": text}}
    result = await engine.execute(runbook, inputs=inputs, trace_id=uuid4())
    if not result.is_success():
        raise RuntimeError(f"Ingest failed: {result.error_message}")
    return result.to_dict()


async def main() -> None:
    md_files = sorted(CONTENT_ROOT.rglob("*.md"))
    if not md_files:
        print(f"No markdown files found under {CONTENT_ROOT}")
        return

    db = await init_db()
    rec_repo = RecognitionRepository(db)
    registry = HandlerRegistry.get_instance()

    engine = RewriterEngine(
        registry=registry,
        db=db,
        measurement_fabric=None,
        known_acts=set(),  # engine will still enforce act presence via registry
        persist_recognitions=True,
        recognition_repo=rec_repo,
    )

    runbook = make_ingest_text_runbook()

    count = 0
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        await ingest_file(engine, runbook, text)
        count += 1

    print(f"Ingested {count} markdown files from {CONTENT_ROOT}")


if __name__ == "__main__":
    asyncio.run(main())

