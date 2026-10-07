"""Exercise the REST skill flow end-to-end with a fake app state.

These tests avoid real DB/skill execution by monkeypatching the app lifecycle
and the skill runner. They ensure:
 - skills are listed from the manifest
 - executing a skill returns structured outputs
"""

from __future__ import annotations

import contextlib
from fastapi.testclient import TestClient

import engine.api.main as main
from engine.api.app_state import AppState
from engine.api.skill_runner import SkillExecutionResponse
import engine.api.api_v1 as api_v1


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
    monkeypatch.setattr(api_v1, "run_skill", fake_run_skill)

    with TestClient(main.app) as client:
        yield client


def test_list_skills(monkeypatch):
    with patched_app(monkeypatch) as client:
        resp = client.get("/api/v1/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["skills"][0]["id"] == "echo"


def test_execute_skill(monkeypatch):
    with patched_app(monkeypatch) as client:
        resp = client.post(
            "/api/v1/skills/echo/execute",
            json={"inputs": {"text": "hello"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["outputs"]["echo"]["text"] == "hello"
