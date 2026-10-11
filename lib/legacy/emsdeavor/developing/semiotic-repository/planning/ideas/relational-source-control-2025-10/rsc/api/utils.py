"""
Shared utilities for API routers.
"""

import sqlite3
from typing import Any


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    """Convert SQLite rows to dictionaries."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
