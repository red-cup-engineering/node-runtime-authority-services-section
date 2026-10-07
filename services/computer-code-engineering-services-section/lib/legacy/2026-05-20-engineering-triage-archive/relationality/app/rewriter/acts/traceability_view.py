from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID, uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class TraceabilityViewHandler(ActHandler):
    """Traceability helper (not a core act).

    Builds a traceability view for a single TracePoint/recognition by
    collecting its content, dependency edges, and audit logs.

    Inputs:
      - tracepoint_id: str (required) – UUID of the TracePoint
    """

    acts: list[str] = []

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        tracepoint_id_str = context.get_input("tracepoint_id")
        if not tracepoint_id_str:
            return HandlerResult.fail("Missing required input: tracepoint_id")

        try:
            tp_id = UUID(str(tracepoint_id_str))
        except Exception:
            return HandlerResult.fail("Invalid tracepoint_id; must be a UUID string")

        db = getattr(context, "db", None)
        if db is None:
            return HandlerResult.fail("Database handle not available in context")

        from app.storage.repositories import RecognitionRepository, AuditRepository

        rec_repo = RecognitionRepository(db)
        audit_repo = AuditRepository(db)

        recognition = await rec_repo.get(tp_id)
        if recognition is None:
            return HandlerResult.fail(f"TracePoint {tp_id} not found")

        edges = await rec_repo.get_edges(tp_id, direction="both")

        audit_logs: List[Dict[str, Any]] = await audit_repo.query(
            entity_type="recognition",
            entity_id=str(tp_id),
            limit=100,
            offset=0,
        )

        now = datetime.utcnow().isoformat()
        view = {
            "id": str(uuid4()),
            "type": "traceability_view",
            "act": act,
            "acts": [act],
            "tracepoint_id": str(tp_id),
            "recognition": recognition.model_dump(mode="json"),
            "edges": edges,
            "audit_logs": audit_logs,
            "constructed_at": now,
            "trace_id": str(context.trace_id),
        }

        # Persist the view itself as a recognition for later inspection.
        view_recognition = {
            "id": view["id"],
            "type": "witness",
            "title": f"Traceability view for {tp_id}",
            "act": act,
            "acts": [act],
            "view": view,
        }

        persisted_id = await context.persist_recognition(view_recognition)

        return HandlerResult.ok(
            outputs={
                "view": view,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
