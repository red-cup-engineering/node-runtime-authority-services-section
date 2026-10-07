"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient

from app import app
from rsc.database import init_database, get_db_connection


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(tmp_path_factory):
    """Set up test database path for all tests."""
    # Create test database
    test_db_path = tmp_path_factory.mktemp("test_db") / "test_rrpr.db"
    init_database(test_db_path)
    
    # Set environment variable so endpoints use test database
    os.environ["DATABASE_PATH"] = str(test_db_path)
    
    yield test_db_path
    
    # Cleanup
    if "DATABASE_PATH" in os.environ:
        del os.environ["DATABASE_PATH"]


@pytest.fixture
def client():
    """FastAPI test client with test database."""
    return TestClient(app)


@pytest.fixture
def db_connection(setup_test_database):
    """Database connection for direct testing."""
    conn = get_db_connection(setup_test_database)
    yield conn
    conn.close()
