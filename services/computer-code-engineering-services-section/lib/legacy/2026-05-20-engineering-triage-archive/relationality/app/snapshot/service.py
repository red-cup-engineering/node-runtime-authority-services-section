"""Snapshot Service for managing snapshot semantics.

Implements the storage simulation specification with:
- Snapshot creation with baseline hash computation
- Context archiving for evaluation state preservation
- Snapshot differencing for incremental updates
- Snapshot restoration and verification
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.snapshot.hasher import BaselineHasher, HashResult
from app.storage.database import Database, get_database


@dataclass
class SnapshotContext:
    """Archived context from a snapshot."""
    
    id: str
    context_type: str
    bindings: dict[str, Any]
    depth: int
    parent_context: Optional[str]
    hash: str
    archived_at: str


@dataclass
class SnapshotResult:
    """Result of a snapshot operation."""
    
    success: bool
    snapshot_id: Optional[str] = None
    baseline_hash: Optional[str] = None
    recognition_count: int = 0
    context_count: int = 0
    trace_count: int = 0
    error: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class DiffResult:
    """Result of comparing two snapshots."""
    
    added_count: int
    removed_count: int
    modified_count: int
    added_ids: list[str] = field(default_factory=list)
    removed_ids: list[str] = field(default_factory=list)
    modified_ids: list[str] = field(default_factory=list)
    diff_hash: Optional[str] = None


class SnapshotService:
    """Service for managing snapshot semantics.
    
    Provides:
    - Point-in-time snapshot creation with baseline hashing
    - Context archiving for preserving evaluation state
    - Incremental diffing between snapshots
    - Snapshot verification and restoration
    """
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db
        self.hasher = BaselineHasher()
        self._context_archive: dict[str, list[SnapshotContext]] = {}
    
    async def _get_db(self) -> Database:
        """Get database connection, initializing if needed."""
        if self.db is None:
            self.db = await get_database()
        return self.db
    
    async def create_snapshot(
        self,
        name: str,
        description: Optional[str] = None,
        include_contexts: bool = True,
        include_traces: bool = True,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SnapshotResult:
        """Create a new snapshot with baseline hash.
        
        Args:
            name: Name for the snapshot
            description: Optional description
            include_contexts: Whether to archive contexts
            include_traces: Whether to archive traces
            metadata: Additional metadata to include
        
        Returns:
            SnapshotResult with snapshot ID and baseline hash
        """
        try:
            db = await self._get_db()
            
            recognitions = await db.fetch_all(
                "SELECT * FROM recognitions ORDER BY created_at"
            )
            recognition_dicts = [dict(row) for row in recognitions]
            
            contexts = []
            traces = []
            
            for rec in recognition_dicts:
                try:
                    import json
                    content = json.loads(rec.get("content", "{}"))
                    rec_type = rec.get("type", "")
                    
                    if include_contexts and rec_type == "context":
                        contexts.append(content)
                    elif include_traces and rec_type == "trace":
                        traces.append(content)
                except Exception:
                    pass
            
            hash_result = self.hasher.hash_snapshot(
                recognitions=recognition_dicts,
                contexts=contexts if include_contexts else None,
                traces=traces if include_traces else None,
                metadata=metadata,
            )
            
            snapshot_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            
            import json
            await db.execute(
                """
                INSERT INTO snapshots (id, name, description, baseline_hash, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    name,
                    description,
                    hash_result.hash,
                    json.dumps({
                        **(metadata or {}),
                        "recognition_count": len(recognition_dicts),
                        "context_count": len(contexts),
                        "trace_count": len(traces),
                        "include_contexts": include_contexts,
                        "include_traces": include_traces,
                    }),
                    now,
                )
            )
            await db.commit()
            
            await db.execute(
                """
                UPDATE recognitions 
                SET snapshot_id = ?, baseline_hash = ?
                WHERE snapshot_id IS NULL
                """,
                (snapshot_id, hash_result.hash)
            )
            await db.commit()
            
            if include_contexts:
                archived_contexts = []
                for ctx in contexts:
                    archived = SnapshotContext(
                        id=ctx.get("id", str(uuid4())),
                        context_type=ctx.get("context_type", "evaluation"),
                        bindings=ctx.get("bindings", {}),
                        depth=ctx.get("depth", 0),
                        parent_context=ctx.get("parent_context"),
                        hash=self.hasher.hash_context(ctx),
                        archived_at=now,
                    )
                    archived_contexts.append(archived)
                
                self._context_archive[snapshot_id] = archived_contexts
            
            return SnapshotResult(
                success=True,
                snapshot_id=snapshot_id,
                baseline_hash=hash_result.hash,
                recognition_count=len(recognition_dicts),
                context_count=len(contexts),
                trace_count=len(traces),
                created_at=now,
            )
        
        except Exception as e:
            return SnapshotResult(
                success=False,
                error=str(e),
            )
    
    async def get_snapshot(self, snapshot_id: str) -> Optional[dict[str, Any]]:
        """Get a snapshot by ID."""
        db = await self._get_db()
        
        row = await db.fetch_one(
            "SELECT * FROM snapshots WHERE id = ?",
            (snapshot_id,)
        )
        
        if not row:
            return None
        
        import json
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "baseline_hash": row["baseline_hash"],
            "metadata": json.loads(row["metadata"]),
            "created_at": row["created_at"],
        }
    
    async def get_snapshot_recognitions(
        self,
        snapshot_id: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Get all recognitions in a snapshot."""
        db = await self._get_db()
        
        rows = await db.fetch_all(
            "SELECT * FROM recognitions WHERE snapshot_id = ? LIMIT ?",
            (snapshot_id, limit)
        )
        
        import json
        return [
            {
                "id": row["id"],
                "type": row["type"],
                "title": row["title"],
                "content": json.loads(row["content"]),
                "acts": json.loads(row["acts"]),
                "baseline_hash": row["baseline_hash"],
            }
            for row in rows
        ]
    
    async def get_archived_contexts(
        self,
        snapshot_id: str,
    ) -> list[SnapshotContext]:
        """Get archived contexts for a snapshot."""
        return self._context_archive.get(snapshot_id, [])
    
    async def diff_snapshots(
        self,
        old_snapshot_id: str,
        new_snapshot_id: str,
    ) -> DiffResult:
        """Compare two snapshots and return the differences."""
        old_recognitions = await self.get_snapshot_recognitions(old_snapshot_id)
        new_recognitions = await self.get_snapshot_recognitions(new_snapshot_id)
        
        old_hashes = {self.hasher.hash_recognition(r): r["id"] for r in old_recognitions}
        new_hashes = {self.hasher.hash_recognition(r): r["id"] for r in new_recognitions}
        
        old_ids = {r["id"] for r in old_recognitions}
        new_ids = {r["id"] for r in new_recognitions}
        
        added_ids = list(new_ids - old_ids)
        removed_ids = list(old_ids - new_ids)
        
        modified_ids = []
        for rec in new_recognitions:
            if rec["id"] in old_ids:
                old_rec = next((r for r in old_recognitions if r["id"] == rec["id"]), None)
                if old_rec:
                    old_hash = self.hasher.hash_recognition(old_rec)
                    new_hash = self.hasher.hash_recognition(rec)
                    if old_hash != new_hash:
                        modified_ids.append(rec["id"])
        
        old_snapshot = await self.get_snapshot(old_snapshot_id)
        new_snapshot = await self.get_snapshot(new_snapshot_id)
        
        old_baseline = old_snapshot.get("baseline_hash", "") if old_snapshot else ""
        new_baseline = new_snapshot.get("baseline_hash", "") if new_snapshot else ""
        
        added_hashes = [self.hasher.hash_recognition(r) for r in new_recognitions if r["id"] in added_ids]
        removed_hashes = [h for h, id in old_hashes.items() if id in removed_ids]
        
        diff_hash = self.hasher.compute_diff_hash(
            old_hash=old_baseline,
            new_hash=new_baseline,
            added_hashes=added_hashes,
            removed_hashes=removed_hashes,
        )
        
        return DiffResult(
            added_count=len(added_ids),
            removed_count=len(removed_ids),
            modified_count=len(modified_ids),
            added_ids=added_ids,
            removed_ids=removed_ids,
            modified_ids=modified_ids,
            diff_hash=diff_hash,
        )
    
    async def verify_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Verify the integrity of a snapshot.
        
        Recomputes the baseline hash and compares to stored hash.
        """
        snapshot = await self.get_snapshot(snapshot_id)
        if not snapshot:
            return {
                "verified": False,
                "error": "Snapshot not found",
            }
        
        recognitions = await self.get_snapshot_recognitions(snapshot_id)
        
        current_hash = self.hasher.hash_collection(recognitions)
        
        stored_hash = snapshot.get("baseline_hash", "")
        
        verified = current_hash.hash == stored_hash
        
        return {
            "verified": verified,
            "snapshot_id": snapshot_id,
            "stored_hash": stored_hash,
            "computed_hash": current_hash.hash,
            "recognition_count": len(recognitions),
            "discrepancy": None if verified else "Hash mismatch - data may have been modified",
        }
    
    async def list_snapshots(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List all snapshots."""
        db = await self._get_db()
        
        rows = await db.fetch_all(
            "SELECT * FROM snapshots ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        
        import json
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "baseline_hash": row["baseline_hash"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
