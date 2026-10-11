"""
Minimal MCP-style server exposing a read-only surface aligned with the FastAPI API.

Protocol (line-delimited JSON over stdin/stdout, canonical JSON formatting):
request: {"id": "<client-correlation>", "method": "list_runbooks"}
response: {"id": "<client-correlation>", "result": {...}} on success
          {"id": "<client-correlation>", "error": {"message": "...", "kind": "..."}}

Methods:
- list_runbooks: returns {"runbooks": [runbook_payloads...]} ordered by ID.

This server is intentionally thin and read-only: it forwards directly to the
underlying loaders and exposes no mutation or interaction methods.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from relationality.runtime import get_computer


def _json_dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _error_response(request_id: Any, message: str, kind: str = "error") -> str:
    return _json_dumps({"id": request_id, "error": {"message": message, "kind": kind}})


def list_runbooks() -> Dict[str, Any]:
    computer = get_computer(require_runtime_viability=True)
    runbooks = computer.runbooks
    rbs = sorted(runbooks.by_id.values(), key=lambda rb: rb["id"])
    if not rbs:
        raise KeyError("no runbooks available")
    return {"runbooks": rbs}


async def handle_request(request: Dict[str, Any]) -> str:
    req_id = request.get("id")
    method = request.get("method")
    try:
        if method == "list_runbooks":
            result = list_runbooks()
        else:
            return _error_response(req_id, f"unknown method {method!r}", kind="unknown_method")
        return _json_dumps({"id": req_id, "result": result})
    except KeyError as exc:
        return _error_response(req_id, str(exc), kind=exc.__class__.__name__)
    except Exception as exc:  # pragma: no cover - defensive guardrail
        return _error_response(req_id, f"internal error: {exc}", kind=exc.__class__.__name__)


async def serve() -> None:
    """
    Run a simple stdin/stdout MCP loop until EOF.
    """
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, input)
        except EOFError:
            break
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            print(_error_response(None, "invalid JSON"), flush=True)
            continue
        response = await handle_request(request)
        print(response, flush=True)


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
