"""Validate OpenAPI schema generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import os
import pytest


BASE_URL = os.getenv("OPENAPI_BASE_URL")


@pytest.mark.skipif(not BASE_URL, reason="Requires OPENAPI_BASE_URL to be set (e.g. http://localhost:5000)")
def test_openapi_has_paths():
    """Ensure OpenAPI schema is generated with paths."""
    import httpx

    resp = httpx.get(f"{BASE_URL}/openapi.json", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    assert "paths" in data and data["paths"]
