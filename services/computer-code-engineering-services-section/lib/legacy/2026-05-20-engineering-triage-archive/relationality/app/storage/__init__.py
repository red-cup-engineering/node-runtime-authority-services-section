"""SQLite-based storage layer for the relational computer.

Implements the storage specification with tables for:
- Snapshots: Point-in-time captures of system state
- TracePoints: Triadic points in traces/contexts
- Edges: Dependency relationships between TracePoints
- Audit logs: Policy decisions and execution traces
"""

from app.storage.database import (
    Database,
    get_db,
    init_db,
)
from app.storage.repositories import (
    RecognitionRepository,
    RunbookRepository,
    SnapshotRepository,
    AuditRepository,
)

__all__ = [
    "Database",
    "get_db",
    "init_db",
    "RecognitionRepository",
    "RunbookRepository",
    "SnapshotRepository",
    "AuditRepository",
]
