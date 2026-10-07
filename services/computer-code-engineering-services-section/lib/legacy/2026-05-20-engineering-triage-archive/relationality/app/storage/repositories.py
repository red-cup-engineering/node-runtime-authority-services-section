"""Repository classes for database operations.

Each repository handles CRUD operations for a specific entity type,
translating between Pydantic models and database rows.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.schemas.recognition import (
    TracePointCreate,
    TracePointSchema,
    TracePointStatus,
    TracePointRole,
    TracePointUpdate,
)
from app.schemas.runbook import (
    RunbookCreate,
    RunbookSchema,
    RunbookStatus,
    RunbookStep,
)
from app.schemas.policy import (
    PolicyAnnotation,
    PolicyDefinition,
    PolicyScope,
)
from app.storage.database import Database


class RecognitionRepository:
    """Repository for TracePoint/Recognition entities.

    Conceptually, each row in the `recognitions` table is a TracePoint: a
    triadic, typed point in a trace/context with attached structure, not the
    primitive Recognition act from the math layer.
    """
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create(self, data: TracePointCreate) -> TracePointSchema:
        """Create a new TracePoint/recognition.

        IDs are derived deterministically from the tracepoint content so that
        structurally identical tracepoints receive the same identifier. This
        is a provisional notion of identity; more refined schemes can be
        introduced once additional stacks (towers, hypertensors, etc.) are
        fully realised.
        """
        # Deterministic identity and baseline hash from the payload.
        payload = {
            "type": data.type.value,
            "title": data.title,
            "content": data.content,
            "acts": data.acts,
            "parent_id": str(data.parent_id) if data.parent_id else None,
            "tags": data.tags,
            "metadata": data.metadata,
        }
        payload_str = json.dumps(payload, sort_keys=True)
        baseline_hash = datetime.utcnow().isoformat()  # fallback if hashing fails
        try:
            import hashlib

            baseline_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        except Exception:
            # If hashing fails for any reason, we still create a tracepoint
            # with a time-based baseline hash; this should be rare.
            pass

        from uuid import uuid5, NAMESPACE_URL

        recognition_id = uuid5(NAMESPACE_URL, payload_str)
        now = datetime.utcnow().isoformat()
        
        await self.db.execute(
            """
            INSERT INTO tracepoints (id, type, title, content, acts, parent_id, tags, metadata, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(recognition_id),
                data.type.value,
                data.title,
                json.dumps(data.content),
                json.dumps(data.acts),
                str(data.parent_id) if data.parent_id else None,
                json.dumps(data.tags),
                json.dumps(data.metadata),
                TracePointStatus.PENDING.value,
                now,
                now,
            )
        )
        await self.db.commit()
        
        await self._log_audit(
            "create",
            "recognition",
            str(recognition_id),
            {"title": data.title, "type": data.type.value}
        )
        
        return TracePointSchema(
            id=recognition_id,
            type=data.type,
            title=data.title,
            content=data.content,
            acts=data.acts,
            parent_id=data.parent_id,
            tags=data.tags,
            metadata=data.metadata,
            status=TracePointStatus.PENDING,
            baseline_hash=baseline_hash,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )
    
    async def get(self, recognition_id: UUID) -> Optional[TracePointSchema]:
        """Get a recognition by ID."""
        row = await self.db.fetch_one(
            "SELECT * FROM tracepoints WHERE id = ?",
            (str(recognition_id),)
        )
        if not row:
            return None
        return self._row_to_schema(row)
    
    async def list(
        self,
        type: Optional[TracePointRole] = None,
        status: Optional[TracePointStatus] = None,
        snapshot_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TracePointSchema]:
        """List recognitions with optional filters."""
        conditions = []
        params: list[Any] = []
        
        if type:
            conditions.append("type = ?")
            params.append(type.value)
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if snapshot_id:
            conditions.append("snapshot_id = ?")
            params.append(str(snapshot_id))
        
        where = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])
        
        rows = await self.db.fetch_all(
            f"SELECT * FROM tracepoints WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            tuple(params)
        )
        return [self._row_to_schema(row) for row in rows]
    
    async def update(
        self,
        recognition_id: UUID,
        data: TracePointUpdate
    ) -> Optional[TracePointSchema]:
        """Update a recognition."""
        existing = await self.get(recognition_id)
        if not existing:
            return None
        
        updates = []
        params: list[Any] = []
        
        if data.title is not None:
            updates.append("title = ?")
            params.append(data.title)
        if data.content is not None:
            updates.append("content = ?")
            params.append(json.dumps(data.content))
        if data.acts is not None:
            updates.append("acts = ?")
            params.append(json.dumps(data.acts))
        if data.tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(data.tags))
        if data.metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(data.metadata))
        if data.status is not None:
            updates.append("status = ?")
            params.append(data.status.value)
        
        if not updates:
            return existing
        
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(str(recognition_id))
        
        await self.db.execute(
            f"UPDATE recognitions SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        await self.db.commit()
        
        await self._log_audit(
            "update",
            "recognition",
            str(recognition_id),
            data.model_dump(exclude_none=True)
        )
        
        return await self.get(recognition_id)
    
    async def delete(self, recognition_id: UUID) -> bool:
        """Delete a recognition."""
        result = await self.db.execute(
            "DELETE FROM tracepoints WHERE id = ?",
            (str(recognition_id),)
        )
        await self.db.commit()
        
        if result.rowcount > 0:
            await self._log_audit("delete", "recognition", str(recognition_id), {})
            return True
        return False
    
    async def add_edge(
        self,
        src_id: UUID,
        dst_id: UUID,
        edge_type: str = "depends_on",
        metadata: Optional[dict] = None
    ) -> bool:
        """Add a dependency edge between recognitions."""
        try:
            await self.db.execute(
                """
                INSERT INTO tracepoint_edges (src_id, dst_id, edge_type, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (str(src_id), str(dst_id), edge_type, json.dumps(metadata or {}))
            )
            await self.db.commit()
            return True
        except Exception:
            return False
    
    async def get_edges(
        self,
        recognition_id: UUID,
        direction: str = "both"
    ) -> dict[str, list[dict]]:
        """Get edges for a recognition."""
        result = {"incoming": [], "outgoing": []}
        
        if direction in ("outgoing", "both"):
            rows = await self.db.fetch_all(
                "SELECT * FROM tracepoint_edges WHERE src_id = ?",
                (str(recognition_id),)
            )
            result["outgoing"] = [dict(row) for row in rows]
        
        if direction in ("incoming", "both"):
            rows = await self.db.fetch_all(
                "SELECT * FROM tracepoint_edges WHERE dst_id = ?",
                (str(recognition_id),)
            )
            result["incoming"] = [dict(row) for row in rows]
        
        return result
    
    def _row_to_schema(self, row) -> TracePointSchema:
        return TracePointSchema(
            id=UUID(row["id"]),
            type=TracePointRole(row["type"]),
            title=row["title"],
            content=json.loads(row["content"]),
            acts=json.loads(row["acts"]),
            parent_id=UUID(row["parent_id"]) if row["parent_id"] else None,
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            status=TracePointStatus(row["status"]),
            snapshot_id=UUID(row["snapshot_id"]) if row["snapshot_id"] else None,
            trace_id=UUID(row["trace_id"]) if row["trace_id"] else None,
            baseline_hash=row["baseline_hash"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    async def _log_audit(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO audit_logs (action, entity_type, entity_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (action, entity_type, entity_id, json.dumps(details))
        )


class RunbookRepository:
    """Repository for Runbook entities."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create(self, data: RunbookCreate) -> RunbookSchema:
        """Create a new runbook."""
        runbook_id = uuid4()
        now = datetime.utcnow().isoformat()
        
        steps_json = json.dumps([step.model_dump() for step in data.steps])
        
        await self.db.execute(
            """
            INSERT INTO runbooks (id, name, description, version, steps, tags, policy_requirements, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(runbook_id),
                data.name,
                data.description,
                data.version,
                steps_json,
                json.dumps(data.tags),
                json.dumps(data.policy_requirements),
                RunbookStatus.DRAFT.value,
                now,
                now,
            )
        )
        await self.db.commit()
        
        return RunbookSchema(
            id=runbook_id,
            name=data.name,
            description=data.description,
            version=data.version,
            steps=data.steps,
            tags=data.tags,
            policy_requirements=data.policy_requirements,
            status=RunbookStatus.DRAFT,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )
    
    async def get(self, runbook_id: UUID) -> Optional[RunbookSchema]:
        """Get a runbook by ID."""
        row = await self.db.fetch_one(
            "SELECT * FROM runbooks WHERE id = ?",
            (str(runbook_id),)
        )
        if not row:
            return None
        return self._row_to_schema(row)
    
    async def list(
        self,
        status: Optional[RunbookStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RunbookSchema]:
        """List runbooks with optional filters."""
        if status:
            rows = await self.db.fetch_all(
                "SELECT * FROM runbooks WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status.value, limit, offset)
            )
        else:
            rows = await self.db.fetch_all(
                "SELECT * FROM runbooks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        return [self._row_to_schema(row) for row in rows]
    
    async def update_status(
        self,
        runbook_id: UUID,
        status: RunbookStatus,
        execution_id: Optional[UUID] = None
    ) -> bool:
        """Update runbook status."""
        params: list[Any] = [status.value, datetime.utcnow().isoformat()]
        sql = "UPDATE runbooks SET status = ?, updated_at = ?"
        
        if execution_id:
            sql += ", last_execution_id = ?, execution_count = execution_count + 1"
            params.append(str(execution_id))
        
        sql += " WHERE id = ?"
        params.append(str(runbook_id))
        
        result = await self.db.execute(sql, tuple(params))
        await self.db.commit()
        return result.rowcount > 0
    
    async def delete(self, runbook_id: UUID) -> bool:
        """Delete a runbook."""
        result = await self.db.execute(
            "DELETE FROM runbooks WHERE id = ?",
            (str(runbook_id),)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    def _row_to_schema(self, row) -> RunbookSchema:
        steps_data = json.loads(row["steps"])
        steps = [RunbookStep.model_validate(s) for s in steps_data]
        
        return RunbookSchema(
            id=UUID(row["id"]),
            name=row["name"],
            description=row["description"],
            version=row["version"],
            steps=steps,
            tags=json.loads(row["tags"]),
            policy_requirements=json.loads(row["policy_requirements"]),
            status=RunbookStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            created_by=row["created_by"],
            last_execution_id=UUID(row["last_execution_id"]) if row["last_execution_id"] else None,
            execution_count=row["execution_count"],
        )


class SnapshotRepository:
    """Repository for Snapshot entities."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create(
        self,
        name: str,
        description: Optional[str] = None,
        baseline_hash: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a new snapshot."""
        snapshot_id = uuid4()
        now = datetime.utcnow().isoformat()
        
        await self.db.execute(
            """
            INSERT INTO snapshots (id, name, description, baseline_hash, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(snapshot_id),
                name,
                description,
                baseline_hash,
                json.dumps(metadata or {}),
                now,
            )
        )
        await self.db.commit()
        
        return {
            "id": snapshot_id,
            "name": name,
            "description": description,
            "baseline_hash": baseline_hash,
            "metadata": metadata or {},
            "created_at": now,
        }
    
    async def get(self, snapshot_id: UUID) -> Optional[dict]:
        """Get a snapshot by ID."""
        row = await self.db.fetch_one(
            "SELECT * FROM snapshots WHERE id = ?",
            (str(snapshot_id),)
        )
        if not row:
            return None
        return {
            "id": UUID(row["id"]),
            "name": row["name"],
            "description": row["description"],
            "baseline_hash": row["baseline_hash"],
            "metadata": json.loads(row["metadata"]),
            "created_at": row["created_at"],
        }
    
    async def list(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """List snapshots."""
        rows = await self.db.fetch_all(
            "SELECT * FROM snapshots ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [
            {
                "id": UUID(row["id"]),
                "name": row["name"],
                "description": row["description"],
                "baseline_hash": row["baseline_hash"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    
    async def get_recognitions(self, snapshot_id: UUID) -> list:
        """Get all recognitions in a snapshot."""
        repo = RecognitionRepository(self.db)
        return await repo.list(snapshot_id=snapshot_id, limit=10000)
    
    async def delete(self, snapshot_id: UUID) -> bool:
        """Delete a snapshot."""
        result = await self.db.execute(
            "DELETE FROM snapshots WHERE id = ?",
            (str(snapshot_id),)
        )
        await self.db.commit()
        return result.rowcount > 0


class AuditRepository:
    """Repository for audit log entries."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        actor: Optional[str] = None,
        details: Optional[dict] = None,
        trace_id: Optional[str] = None,
        policy_decision: Optional[str] = None,
    ) -> int:
        """Create an audit log entry."""
        cursor = await self.db.execute(
            """
            INSERT INTO audit_logs (action, entity_type, entity_id, actor, details, trace_id, policy_decision)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action,
                entity_type,
                entity_id,
                actor,
                json.dumps(details or {}),
                trace_id,
                policy_decision,
            )
        )
        await self.db.commit()
        return cursor.lastrowid or 0
    
    async def query(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        trace_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Query audit logs with filters."""
        conditions = []
        params: list[Any] = []
        
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        where = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])
        
        rows = await self.db.fetch_all(
            f"SELECT * FROM audit_logs WHERE {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            tuple(params)
        )
        
        return [
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "actor": row["actor"],
                "details": json.loads(row["details"]),
                "trace_id": row["trace_id"],
                "policy_decision": row["policy_decision"],
            }
            for row in rows
        ]
