"""MCP adapter smoke: tools/list and resources/list/read via SDK router."""

from __future__ import annotations

import json
import contextlib

from fastapi.testclient import TestClient

import engine.api.main as main
from engine.api.app_state import AppState
from engine.api.skill_runner import SkillExecutionResponse


def make_fake_state() -> AppState:
    state = AppState()
    state.is_ready = True
    state.manifest = {
        "version": "1.0.0",
        "spec_version": "1",
        "skill_count": 1,
        "skills": [
            {
                "id": "echo",
                "name": "Echo",
                "summary": "Echo back inputs",
                "path": "skills/echo",
                "runtime": {"entrypoint": "skills/echo/run.sh", "language": "shell"},
                "skill_spec_version": "1",
                "inputs": [{"name": "text", "type": "string", "required": True}],
            }
        ],
    }
    return state


@contextlib.contextmanager
def patched_app(monkeypatch):
    fake_state = make_fake_state()

    async def fake_create_app_state():
        return fake_state

    async def fake_shutdown_app_state(state):
        return None

    def fake_run_skill(skill, inputs):
        return SkillExecutionResponse(
            success=True,
            skill_id=skill.get("id", "unknown"),
            outputs={"echo": inputs},
            stdout=None,
            stderr=None,
            error=None,
        )

    monkeypatch.setattr(main, "create_app_state", fake_create_app_state)
    monkeypatch.setattr(main, "shutdown_app_state", fake_shutdown_app_state)
    monkeypatch.setattr("engine.api.api_v1.run_skill", fake_run_skill)

    with TestClient(main.app) as client:
        yield client


def test_mcp_tools_list(monkeypatch):
    with patched_app(monkeypatch) as client:
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("result") and "tools" in data["result"]


def test_mcp_resources_list(monkeypatch):
    with patched_app(monkeypatch) as client:
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("result") and "resources" in data["result"]
