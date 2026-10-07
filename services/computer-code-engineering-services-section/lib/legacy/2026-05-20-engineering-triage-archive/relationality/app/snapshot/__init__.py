"""Snapshot Semantics for the relational computer.

Implements the storage simulation specification with:
- Baseline hash computation for content integrity
- Context archiving for evaluation state preservation
- Snapshot differencing for incremental updates
"""

from app.snapshot.service import SnapshotService
from app.snapshot.hasher import BaselineHasher

__all__ = [
    "SnapshotService",
    "BaselineHasher",
]
