"""MCP smoke tests using httpx against a live app instance.

These are placeholder tests; they assume the app is running locally on :5000.
"""

import os
import pytest
import httpx


BASE_URL = os.environ.get("MCP_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="MCP_BASE_URL required for MCP smoke")


def test_tools_list():
    resp = httpx.post(
        f"{BASE_URL}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        timeout=5,
    )
    assert resp.status_code == 200


def test_resources_list():
    resp = httpx.post(
        f"{BASE_URL}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}},
        timeout=5,
    )
    assert resp.status_code == 200
