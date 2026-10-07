"""SQLite database connection and initialization.

Uses aiosqlite for async operations, with a connection pool pattern
suitable for the FastAPI async context.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Optional
from uuid import UUID

import aiosqlite


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "relational.db"


def uuid_adapter(val: UUID) -> str:
    return str(val)


def uuid_converter(val: bytes) -> UUID:
    return UUID(val.decode())


def datetime_adapter(val: datetime) -> str:
    return val.isoformat()


def datetime_converter(val: bytes) -> datetime:
    return datetime.fromisoformat(val.decode())


def json_adapter(val: dict | list) -> str:
    return json.dumps(val)


def json_converter(val: bytes) -> dict | list:
    return json.loads(val.decode())


sqlite3.register_adapter(UUID, uuid_adapter)
sqlite3.register_converter("UUID", uuid_converter)
sqlite3.register_adapter(datetime, datetime_adapter)
sqlite3.register_converter("DATETIME", datetime_converter)


SCHEMA_SQL = """
-- Snapshots: Point-in-time captures of system state
CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    baseline_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT DEFAULT '{}'
);

-- TracePoints: Triadic points in traces/contexts
CREATE TABLE IF NOT EXISTS tracepoints (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN ('observation', 'judgement', 'witness', 'context', 'trace')),
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '{}',
    acts TEXT NOT NULL DEFAULT '[]',
    parent_id TEXT REFERENCES recognitions(id),
    tags TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'validated', 'rejected', 'archived')),
    snapshot_id TEXT REFERENCES snapshots(id),
    trace_id TEXT,
    baseline_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tracepoints_type ON tracepoints(type);
CREATE INDEX IF NOT EXISTS idx_tracepoints_status ON tracepoints(status);
CREATE INDEX IF NOT EXISTS idx_tracepoints_snapshot ON tracepoints(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_tracepoints_parent ON tracepoints(parent_id);
CREATE INDEX IF NOT EXISTS idx_tracepoints_trace ON tracepoints(trace_id);

-- Edges: Dependency relationships between TracePoints
CREATE TABLE IF NOT EXISTS tracepoint_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_id TEXT NOT NULL REFERENCES tracepoints(id),
    dst_id TEXT NOT NULL REFERENCES tracepoints(id),
    edge_type TEXT NOT NULL DEFAULT 'depends_on',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(src_id, dst_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_edges_src ON tracepoint_edges(src_id);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON tracepoint_edges(dst_id);

-- Runbooks: Stored runbook definitions
CREATE TABLE IF NOT EXISTS runbooks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    version TEXT NOT NULL DEFAULT '1.0.0',
    steps TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]',
    policy_requirements TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'validated', 'running', 'completed', 'failed', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT,
    last_execution_id TEXT,
    execution_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_runbooks_status ON runbooks(status);

-- Runbook executions: Execution history
CREATE TABLE IF NOT EXISTS runbook_executions (
    id TEXT PRIMARY KEY,
    runbook_id TEXT NOT NULL REFERENCES runbooks(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    started_at TEXT,
    completed_at TEXT,
    step_results TEXT NOT NULL DEFAULT '{}',
    input_params TEXT NOT NULL DEFAULT '{}',
    output_data TEXT NOT NULL DEFAULT '{}',
    error_message TEXT,
    trace_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_executions_runbook ON runbook_executions(runbook_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON runbook_executions(status);

-- Policies: Stored policy definitions
CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    version TEXT NOT NULL DEFAULT '1.0.0',
    scope TEXT NOT NULL DEFAULT 'recognition' CHECK(scope IN ('recognition', 'runbook', 'step', 'snapshot', 'global')),
    disciplines TEXT NOT NULL DEFAULT '[]',
    filters TEXT NOT NULL DEFAULT '[]',
    default_effect TEXT NOT NULL DEFAULT 'deny' CHECK(default_effect IN ('allow', 'deny', 'require_approval')),
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Policy annotations: Authorization records
CREATE TABLE IF NOT EXISTS policy_annotations (
    id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies(id),
    scope TEXT NOT NULL DEFAULT 'recognition',
    target_id TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    granted_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,
    conditions TEXT DEFAULT '{}',
    justification TEXT
);

CREATE INDEX IF NOT EXISTS idx_annotations_policy ON policy_annotations(policy_id);
CREATE INDEX IF NOT EXISTS idx_annotations_target ON policy_annotations(target_id);

-- Audit logs: Complete audit trail
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    actor TEXT,
    details TEXT DEFAULT '{}',
    trace_id TEXT,
    policy_decision TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_logs(trace_id);
"""


class Database:
    """Async SQLite database wrapper."""
    
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Establish database connection and initialize schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self._connection.row_factory = aiosqlite.Row
        await self._connection.executescript(SCHEMA_SQL)
        await self._connection.commit()
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    @property
    def connection(self) -> aiosqlite.Connection:
        if not self._connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection
    
    async def execute(
        self,
        sql: str,
        params: tuple | dict = ()
    ) -> aiosqlite.Cursor:
        """Execute a SQL statement."""
        return await self.connection.execute(sql, params)
    
    async def executemany(
        self,
        sql: str,
        params_seq: list[tuple | dict]
    ) -> aiosqlite.Cursor:
        """Execute a SQL statement with multiple parameter sets."""
        return await self.connection.executemany(sql, params_seq)
    
    async def fetch_one(
        self,
        sql: str,
        params: tuple | dict = ()
    ) -> Optional[aiosqlite.Row]:
        """Fetch a single row."""
        cursor = await self.execute(sql, params)
        return await cursor.fetchone()
    
    async def fetch_all(
        self,
        sql: str,
        params: tuple | dict = ()
    ) -> list[aiosqlite.Row]:
        """Fetch all rows."""
        cursor = await self.execute(sql, params)
        return await cursor.fetchall()
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.connection.commit()
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.connection.rollback()


_db_instance: Optional[Database] = None


async def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> Database:
    """Initialize the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
        await _db_instance.connect()
    return _db_instance


def get_db() -> Database:
    """Get the global database instance."""
    if _db_instance is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db_instance


@asynccontextmanager
async def database_session(db_path: Path | str = DEFAULT_DB_PATH) -> AsyncIterator[Database]:
    """Context manager for database sessions."""
    db = await init_db(db_path)
    try:
        yield db
    finally:
        pass
