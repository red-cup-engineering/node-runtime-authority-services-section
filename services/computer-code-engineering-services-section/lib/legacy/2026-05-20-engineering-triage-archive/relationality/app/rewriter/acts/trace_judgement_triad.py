from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class TraceJudgementTriadHandler(ActHandler):
    """Per-act handler for ``trace-judgement-triad``.

    Given a Trace and a seeded judgement triad, record a TracePoint that
    threads the triad along the judgement trace, matching the
    Trace Judgement Triad act.

    Inputs
    ------
    trace: dict
        The current trace recognition (with an 'id').
    triad: dict
        A judgement triad recognition produced by seed-judgement-triad.
    """

    acts = ["trace-judgement-triad"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace = context.get_input("trace")
        triad = context.get_input("triad")

        if not trace or not triad:
            return HandlerResult.fail("Missing required inputs: trace, triad")

        trace_id = trace.get("id")
        triad_id = triad.get("id")
        if not trace_id or not triad_id:
            return HandlerResult.fail("Trace and triad must have ids")

        now = datetime.utcnow().isoformat()

        traced_triad = {
            "id": str(uuid4()),
            "type": "trace_judgement_triad",
            "title": "Trace of judgement triad",
            "act": act,
            "acts": [act],
            "trace_id": str(context.trace_id),
            "judgement_trace_id": trace_id,
            "triad_id": triad_id,
            "context": triad.get("context"),
            "term": triad.get("term"),
            "observation": triad.get("observation"),
            "threaded_at": now,
        }

        persisted_id = await context.persist_recognition(traced_triad)

        # Optionally, record logical linkage using the recognition repository
        # if available; this is an implementation detail, not a math act.
        repo = getattr(context, "recognition_repo", None)
        if repo is not None:
            try:
                from app.storage.repositories import RecognitionRepository  # noqa: F401
                from uuid import UUID

                await repo.add_edge(
                    src_id=UUID(str(triad_id)),
                    dst_id=UUID(str(persisted_id)),
                    edge_type="triad-threaded-along-trace",
                    metadata={"trace_recognition_id": trace_id},
                )
            except Exception:
                # Edge creation failures should not break the act; the
                # content-level recognition remains valid.
                pass

        return HandlerResult.ok(
            outputs={"traced_triad": traced_triad},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

