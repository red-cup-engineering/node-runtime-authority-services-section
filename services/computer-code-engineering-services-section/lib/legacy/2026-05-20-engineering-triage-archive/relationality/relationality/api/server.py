from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from pydantic import BaseModel

from relationality.runtime import get_computer
from relationality.validation import LawValidationError
from relationality.api.rdf_projection import carriers_to_jsonld, carriers_to_turtle
from relationality.evaluate import evaluate_runbook_by_id

import hashlib
import math


app = FastAPI(
    title="Relational Computer",
    version="0.1.0",
    description="Proof engine and graph for relational mathematics programs.",
)

# Boot the relational computer once on import (and reuse it across all
# handlers): load the canonical carriers/runbooks, enforce graph and
# runtime laws, and resolve realizer modules.
COMPUTER = get_computer(require_runtime_viability=True)


def _object_size_hint(obj: dict) -> int:
    """
    Coarse size proxy used to modulate signature colors.
    """
    kind = obj.get("kind")
    if kind == "profile_topos":
        return len(obj.get("elements", []))
    if kind == "phase_space":
        return len(obj.get("states", []))
    if kind == "trace":
        return len(obj.get("elements", []))
    # Fallback: number of keys.
    return len(obj.keys())


def _hsl_for_kind_and_size(kind: str, size: int) -> str:
    """
    Deterministically map (kind, size) to an HSL color.
    """
    base = int(hashlib.sha256(kind.encode("utf-8")).hexdigest()[:4], 16)
    hue = base % 360
    size_clamped = max(0, min(size, 32))
    sat = 40 + size_clamped // 2  # 40–56
    light = 35 + size_clamped // 2  # 35–51
    return f"hsl({hue}, {sat}%, {light}%)"


def _ring_segment_path(r_inner: float, r_outer: float, start_deg: float, end_deg: float) -> str:
    """
    Build an SVG path for an annular segment from start_deg to end_deg.
    """
    start_rad = math.radians(start_deg)
    end_rad = math.radians(end_deg)
    cx, cy = 50.0, 50.0
    x1_outer = cx + r_outer * math.cos(start_rad)
    y1_outer = cy + r_outer * math.sin(start_rad)
    x2_outer = cx + r_outer * math.cos(end_rad)
    y2_outer = cy + r_outer * math.sin(end_rad)
    x2_inner = cx + r_inner * math.cos(end_rad)
    y2_inner = cy + r_inner * math.sin(end_rad)
    x1_inner = cx + r_inner * math.cos(start_rad)
    y1_inner = cy + r_inner * math.sin(start_rad)
    large_arc = 1 if (end_deg - start_deg) % 360 > 180 else 0
    return (
        f"M {x1_outer:.2f} {y1_outer:.2f} "
        f"A {r_outer:.2f} {r_outer:.2f} 0 {large_arc} 1 {x2_outer:.2f} {y2_outer:.2f} "
        f"L {x2_inner:.2f} {y2_inner:.2f} "
        f"A {r_inner:.2f} {r_inner:.2f} 0 {large_arc} 0 {x1_inner:.2f} {y1_inner:.2f} Z"
    )


def _object_signature_bar(obj: dict) -> str:
    """
    Render an 8x8 glyph summarizing an object's kind and coarse size.

    Each cell is colored from a small palette derived from:
    - kind (base hue),
    - size (saturation/lightness modulation),
    producing a QR-like, multi-color mark that is stable for the same
    carrier but visually distinguishes different kinds/sizes.
    """
    kind = obj.get("kind", "unknown")
    size = _object_size_hint(obj)
    # Center color encodes kind.
    center_color = _hsl_for_kind_and_size(kind, 0)
    parts: list[str] = []
    # Center disk.
    parts.append(f'<circle cx="50" cy="50" r="8" fill="{center_color}" />')

    # Rings: [(segments, r_inner, r_outer)]
    rings = [
        (2, 10.0, 18.0),
        (3, 20.0, 28.0),
        (4, 30.0, 38.0),
        (8, 40.0, 48.0),
    ]
    for ring_index, (segments, r_inner, r_outer) in enumerate(rings, start=1):
        for seg_index in range(segments):
            # Start at -90 deg (12 o'clock) and proceed clockwise.
            span = 360.0 / segments
            start_deg = -90.0 + seg_index * span
            end_deg = start_deg + span
            # Color derived from (kind, size, ring, segment).
            color = _hsl_for_kind_and_size(
                f"{kind}:r{ring_index}:s{seg_index}",
                size,
            )
            path_d = _ring_segment_path(r_inner, r_outer, start_deg, end_deg)
            parts.append(f'<path d="{path_d}" fill="{color}" />')

    svg = (
        '<svg class="signature-bar" width="64" height="64" viewBox="0 0 100 100" '
        'role="img" aria-hidden="true">'
        + "".join(parts)
        + "</svg>"
    )
    return svg


def _runbook_signature_bar(runbook: dict) -> str:
    """
    Render an 8x8 glyph summarizing a runbook's operator sequence.
    """
    name = runbook.get("name", "")
    steps = runbook.get("steps", [])
    kind = f"runbook:{name}"
    size = len(steps)
    center_color = _hsl_for_kind_and_size(kind, 0)
    parts: list[str] = []
    parts.append(f'<circle cx="50" cy="50" r="8" fill="{center_color}" />')

    rings = [
        (2, 10.0, 18.0),
        (3, 20.0, 28.0),
        (4, 30.0, 38.0),
        (8, 40.0, 48.0),
    ]
    for ring_index, (segments, r_inner, r_outer) in enumerate(rings, start=1):
        for seg_index in range(segments):
            span = 360.0 / segments
            start_deg = -90.0 + seg_index * span
            end_deg = start_deg + span
            # Color derived from (kind, step count, ring, segment).
            color = _hsl_for_kind_and_size(
                f"{kind}:r{ring_index}:s{seg_index}",
                size,
            )
            path_d = _ring_segment_path(r_inner, r_outer, start_deg, end_deg)
            parts.append(f'<path d="{path_d}" fill="{color}" />')

    svg = (
        '<svg class="signature-bar" width="64" height="64" viewBox="0 0 100 100" '
        'role="img" aria-hidden="true">'
        + "".join(parts)
        + "</svg>"
    )
    return svg


def _runbook_ribbon(runbook: dict) -> str:
    """
    Render a horizontal ribbon summarizing a runbook's operator sequence.

    Each operator becomes a colored segment; hue is derived from the
    operator name and segment index, so common operator families are
    recognizable across runbooks.
    """
    steps = sorted(runbook.get("steps", []), key=lambda s: s.get("step_index", 0))
    if not steps:
        return '<span class="meta">no steps</span>'
    n = len(steps)
    segments: list[str] = []
    for idx, step in enumerate(steps):
        op = str(step.get("operator") or "")
        color = _hsl_for_kind_and_size(f"op:{op}", idx + 1)
        x = idx
        segments.append(
            f'<rect x="{x}" y="0" width="1" height="10" fill="{color}">'
            f'<title>{op}</title>'
            f"</rect>"
        )
    svg = (
        f'<svg class="runbook-ribbon" viewBox="0 0 {n} 10" '
        'role="img" aria-hidden="true">'
        + "".join(segments)
        + "</svg>"
    )
    return svg


def _build_kind_operator_index(runbooks_by_id: dict[str, dict]) -> dict[frozenset[str], set[str]]:
    """
    Build an index from unordered {kind1, kind2} pairs to operator names
    that mention both kinds in a single step.
    """
    index: dict[frozenset[str], set[str]] = {}
    for rb in runbooks_by_id.values():
        for step in rb.get("steps", []):
            op = step.get("operator")
            if not isinstance(op, str):
                continue
            kinds: list[str] = []
            for spec in step.get("inputs", []):
                k = spec.get("kind")
                if isinstance(k, str):
                    kinds.append(k)
            for spec in step.get("outputs", []):
                k = spec.get("kind")
                if isinstance(k, str):
                    kinds.append(k)
            # Deduplicate within the step.
            unique_kinds = sorted(set(kinds))
            for i in range(len(unique_kinds)):
                for j in range(i + 1, len(unique_kinds)):
                    key = frozenset({unique_kinds[i], unique_kinds[j]})
                    index.setdefault(key, set()).add(op)
    return index


def _object_relation_map(
    center: dict,
    referenced: set[str],
    referenced_by: set[str],
    objects_by_id: dict[str, dict],
    kind_operator_index: dict[frozenset[str], set[str]],
) -> str:
    """
    Render a shallow relational map around a center object.

    Nodes: center + neighbors (depth 1).
    Edges: typed by operator families observed in runbook steps relating
    the kinds of the center and neighbor carriers.
    """
    center_kind = center.get("kind", "unknown")
    center_size = _object_size_hint(center)
    neighbors_ids = sorted(referenced | referenced_by)
    if not neighbors_ids:
        return '<span class="meta">no relational map</span>'
    # Limit for clarity.
    max_neighbors = 12
    neighbors_ids = neighbors_ids[:max_neighbors]

    cx, cy = 50.0, 50.0
    radius = 34.0
    parts: list[str] = []
    # Center node.
    center_color = _hsl_for_kind_and_size(center_kind, center_size)
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{center_color}" />')

    neighbor_points: dict[str, tuple[float, float]] = {}
    n = len(neighbors_ids)
    for idx, nid in enumerate(neighbors_ids):
        obj = objects_by_id.get(nid)
        if not isinstance(obj, dict):
            continue
        angle = math.radians(-90.0 + idx * 360.0 / max(n, 1))
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        neighbor_points[nid] = (x, y)
        kind = obj.get("kind", "unknown")
        size = _object_size_hint(obj)
        color = _hsl_for_kind_and_size(kind, size)
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}">'
            f'<title>{kind} → {nid}</title>'
            f"</circle>"
        )

    # Center → neighbor edges.
    for nid, (x, y) in neighbor_points.items():
        obj = objects_by_id.get(nid) or {}
        kind = obj.get("kind", "unknown")
        key = frozenset({center_kind, kind})
        ops = kind_operator_index.get(key) or set()
        if ops:
            op_name = sorted(ops)[0]
            color = _hsl_for_kind_and_size(f"op:{op_name}", len(ops))
            title = f"{center_kind}↔{kind}: {', '.join(sorted(ops))}"
        else:
            color = "var(--border)"
            title = f"{center_kind}↔{kind}"
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.2f}" y2="{y:.2f}" '
            f'stroke="{color}" stroke-width="1.2">'
            f'<title>{title}</title>'
            f"</line>"
        )

    svg = (
        '<svg class="projection-plot" viewBox="0 0 100 90" '
        'role="img" aria-hidden="true">'
        + "".join(parts)
        + "</svg>"
    )
    return svg


@app.get("/api")
def api_index() -> dict:
    """
    JSON API index.

    Returns a stable mapping from logical operation names to concrete
    HTTP endpoints. The response payload has the form:

    ```json
    {
      "objects": "/api/objects",
      "runbooks": "/api/runbooks",
      "evaluate_runbook": "/api/runbooks/{runbook_id}/evaluate"
    }
    ```

    All URLs are absolute paths on the same host. No mutation occurs as
    a result of calling this endpoint.
    """
    return {
        "objects": "/api/objects",
        "runbooks": "/api/runbooks",
        "evaluate_runbook": "/api/runbooks/{runbook_id}/evaluate",
    }


@app.get("/rdf")
def rdf_index() -> dict:
    """
    RDF (Turtle) index.

    Returns a mapping from logical RDF resources to Turtle projections.
    The response payload has the form:

    ```json
    {
      "objects": "/rdf/objects/{object_id}.ttl",
      "runbooks": "/rdf/runbooks/{runbook_id}.ttl"
    }
    ```

    Each template path yields a read-only Turtle projection of the
    corresponding canonical carrier when invoked.
    """
    return {
        "objects": "/rdf/objects/{object_id}.ttl",
        "runbooks": "/rdf/runbooks/{runbook_id}.ttl",
    }


@app.get("/mcp")
def mcp_index() -> dict:
    """
    MCP interface description (protocol is stdin/stdout, not HTTP).

    Describes how to launch the MCP server and which SSE bridge endpoint
    is available from this HTTP surface. The response payload has the
    form:

    ```json
    {
      "protocol": "line-delimited JSON over stdin/stdout",
      "entrypoint": "python -m relationality.api.mcp_server",
      "sse": "/mcp/sse?method=list_runbooks"
    }
    ```
    """
    return {
        "protocol": "line-delimited JSON over stdin/stdout",
        "entrypoint": "python -m relationality.api.mcp_server",
        "sse": "/mcp/sse?method=list_runbooks",
    }


@app.get("/api/objects")
def list_objects(request: Request):
    """
    List all persisted carriers as objects, with optional JSON-LD view.

    The default response is JSON of the form:

    ```json
    {
      "objects": [ { /* canonical object payload */ }, ... ]
    }
    ```

    Objects are sorted by ascending `id`. If the `Accept` header
    contains `application/ld+json`, the response is a JSON-LD projection
    of the same carriers instead, with media type `application/ld+json`.
    This endpoint is read-only and does not mutate any state.
    """
    objects = COMPUTER.objects
    carriers = sorted(objects.by_id.values(), key=lambda obj: obj["id"])
    accept = request.headers.get("accept", "")
    if "application/ld+json" in accept:
        jsonld = carriers_to_jsonld(carriers, objects.by_id)
        return JSONResponse(content=jsonld, media_type="application/ld+json")
    return {"objects": carriers}


@app.get("/api/objects/{object_id}")
def get_object(object_id: str, request: Request):
    """
    Return a single object carrier, with optional JSON-LD view.

    On success, returns the canonical JSON payload for the carrier with
    the given `object_id`. If the `Accept` header contains
    `application/ld+json`, returns a JSON-LD projection instead.

    On failure (unknown `object_id`), responds with HTTP 404.
    """
    objects = COMPUTER.objects
    obj = objects.by_id.get(object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"object {object_id} not found")
    accept = request.headers.get("accept", "")
    if "application/ld+json" in accept:
        jsonld = carriers_to_jsonld([obj], objects.by_id)
        return JSONResponse(content=jsonld, media_type="application/ld+json")
    return obj


class RunbookEvalRequest(BaseModel):
    bindings: dict[str, str]
    persist: bool = False


@app.post("/api/runbooks/{runbook_id}/evaluate")
def api_evaluate_runbook(runbook_id: str, payload: RunbookEvalRequest):
    """
    Evaluate a runbook against persisted carriers in a local AOG view.

    **Request**

    - Method: POST
    - Path: `/api/runbooks/{runbook_id}/evaluate`
    - Body (JSON), matching `RunbookEvalRequest`:

      ```json
      {
        "bindings": {
          "<role_name>": "<carrier_id>",
          "…": "…"
        },
        "persist": false
      }
      ```

    `bindings` supplies a mapping from runbook input role names to
    carrier IDs. `persist = false` evaluates in an ephemeral local view;
    `persist = true` commits any new carriers back to the canonical
    object store.

    **Response**

    On success, returns:

    ```json
    {
      "bindings": { "<role_name>": "<carrier_id>", "…": "…" },
      "new_objects": [ { /* canonical payloads for any created carriers */ } ]
    }
    ```

    On failure (unknown runbook, bad bindings, or law violation), the
    endpoint responds with HTTP 400 and a JSON payload describing the
    error.
    """
    try:
        new_objects, bindings = evaluate_runbook_by_id(
            runbook_id,
            payload.bindings,
            persist=payload.persist,
        )
    except (KeyError, LawValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "bindings": bindings,
        "new_objects": new_objects,
    }


@app.get("/api/runbooks")
def list_runbooks(request: Request):
    """
    List all persisted runbooks, with optional JSON-LD view.

    The default response is JSON of the form:

    ```json
    {
      "runbooks": [ { /* canonical runbook payload */ }, ... ]
    }
    ```

    Runbooks are sorted by ascending `id`. If the `Accept` header
    contains `application/ld+json`, the response is a JSON-LD projection
    of the same runbooks instead. This endpoint is read-only.
    """
    runbooks = COMPUTER.runbooks
    carriers = sorted(runbooks.by_id.values(), key=lambda rb: rb["id"])
    accept = request.headers.get("accept", "")
    if "application/ld+json" in accept:
        jsonld = carriers_to_jsonld(carriers, runbooks.by_id)
        return JSONResponse(content=jsonld, media_type="application/ld+json")
    return {"runbooks": carriers}


@app.get("/api/runbooks/{runbook_id}")
def get_runbook(runbook_id: str, request: Request):
    """
    Return a single runbook payload, with optional JSON-LD view.

    On success, returns the canonical JSON payload for the runbook with
    the given `runbook_id`. If the `Accept` header contains
    `application/ld+json`, returns a JSON-LD projection instead.

    On failure (unknown `runbook_id`), responds with HTTP 404.
    """
    runbooks = COMPUTER.runbooks
    rb = runbooks.by_id.get(runbook_id)
    if rb is None:
        raise HTTPException(status_code=404, detail=f"runbook {runbook_id} not found")
    accept = request.headers.get("accept", "")
    if "application/ld+json" in accept:
        jsonld = carriers_to_jsonld([rb], runbooks.by_id)
        return JSONResponse(content=jsonld, media_type="application/ld+json")
    return rb


@app.get("/rdf/objects/{object_id}.ttl")
def object_turtle(object_id: str) -> Response:
    """
    RDF (Turtle) representation of a single object carrier.

    On success, returns a `text/turtle` document projecting the given
    canonical object into RDF. On failure (unknown `object_id`),
    responds with HTTP 404.
    """
    objects = COMPUTER.objects
    obj = objects.by_id.get(object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"object {object_id} not found")
    turtle = carriers_to_turtle(
        carriers=[obj],
        node_ids=objects.by_id.keys(),
        header_lines=[
            "# Turtle projection of object carrier",
            f"# object_id: {object_id}",
        ],
    )
    return Response(content=turtle, media_type="text/turtle")


@app.get("/rdf/runbooks/{runbook_id}.ttl")
def runbook_turtle(runbook_id: str) -> Response:
    """
    RDF (Turtle) representation of a single runbook.

    On success, returns a `text/turtle` document projecting the given
    runbook into RDF. On failure (unknown `runbook_id`), responds with
    HTTP 404.
    """
    runbooks = COMPUTER.runbooks
    rb = runbooks.by_id.get(runbook_id)
    if rb is None:
        raise HTTPException(status_code=404, detail=f"runbook {runbook_id} not found")
    turtle = carriers_to_turtle(
        carriers=[rb],
        node_ids=runbooks.by_id.keys(),
        header_lines=[
            "# Turtle projection of runbook",
            f"# runbook_id: {runbook_id}",
        ],
    )
    return Response(content=turtle, media_type="text/turtle")


@app.get("/mcp/sse")
async def mcp_sse(method: str) -> StreamingResponse:
    """
    Minimal MCP-over-SSE endpoint.

    This is a read-only surface exposing selected MCP methods over
    Server-Sent Events (SSE). Each GET request encodes a single MCP
    request via query parameters and returns exactly one `data:` event
    with either:

    - `{"result": ...}` on success, or
    - `{"error": {"message": "...", "kind": "..."}}` on failure.

    Supported `method` values:

    - `list_runbooks` – yields the same data as `mcp_server.list_runbooks()`.

    The SSE stream always terminates after emitting a single event.
    """
    import asyncio
    import json

    from relationality.api import mcp_server

    async def event_stream():
        try:
            if method == "list_runbooks":
                # Reuse the MCP listing helper, which in turn consults the
                # same canonical runbook index.
                result = mcp_server.list_runbooks()
                payload = {"result": result}
            else:
                raise ValueError(f"unknown MCP method {method!r}")
        except Exception as exc:  # pragma: no cover - defensive
            payload = {"error": {"message": str(exc), "kind": exc.__class__.__name__}}
        data = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        yield f"data: {data}\n\n"
        await asyncio.sleep(0)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _html_page(title: str, body: str) -> HTMLResponse:
    """
    Minimal HTML page wrapper for the read-only frontend.
    """
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root[data-theme="dark"] {{
      --bg: #050814;
      --bg-alt: #0b1020;
      --border: #20263b;
      --accent: #8bc5ff;
      --accent-soft: #243b73;
      --text: #f5f5f7;
      --muted: #9ea6c5;
      --code-bg: #161b30;
    }}
    :root[data-theme="light"] {{
      --bg: #fdfdfb;
      --bg-alt: #f7f7f5;
      --border: #e1e1dd;
      --accent: #005f99;
      --accent-soft: #e3eef8;
      --text: #111111;
      --muted: #777777;
      --code-bg: #f3f3ef;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    header[role="banner"] {{
      background: var(--bg-alt);
      border-bottom: 1px solid var(--border);
      padding: 0.75rem 1.75rem 1rem;
    }}
    header[role="banner"] h1 {{
      margin: 0 0 0.25rem 0;
      font-size: 1.25rem;
    }}
    header[role="banner"] nav a {{
      margin-right: 1rem;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    header[role="banner"] nav a:hover {{
      color: var(--accent);
    }}
    .theme-toggle {{
      border-radius: 999px;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 0.15rem 0.6rem;
      cursor: pointer;
    }}
    .theme-toggle:focus-visible {{
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }}
    main {{
      max-width: 960px;
      margin: 1.5rem auto 2rem;
      padding: 0 1.5rem;
    }}
    main h2 {{
      margin-top: 0;
      font-size: 1.1rem;
      color: var(--muted);
    }}
    ul {{
      line-height: 1.4;
    }}
    pre {{
      background: var(--code-bg);
      border-radius: 4px;
      padding: 1rem;
      font-size: 0.85rem;
      overflow-x: auto;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 0.9em;
    }}
    .meta {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .stacked-list {{
      list-style: none;
      padding-left: 0;
    }}
    .stacked-list > li {{
      margin-bottom: 0.4rem;
    }}
    .section-header {{
      font-size: 0.95rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-top: 1.5rem;
      margin-bottom: 0.5rem;
    }}
    .badge {{
      display: inline-block;
      padding: 0.1rem 0.5rem;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
.signature-bar {{
      display: inline-block;
      width: 4rem;
      height: 4rem;
      margin-right: 0.75rem;
      vertical-align: middle;
    }}
    .runbook-ribbon {{
      display: block;
      width: 100%;
      max-width: 520px;
      height: 1.1rem;
      margin: 0.25rem 0 0.75rem 0;
    }}
    .projection-plot {{
      display: block;
      width: 6rem;
      height: 5rem;
      margin: 0.25rem 0 0.75rem 0;
    }}
    dl {{
      margin: 0;
    }}
    dt {{
      font-weight: 600;
      margin-top: 0.5rem;
      font-size: 0.9rem;
    }}
    dd {{
      margin: 0 0 0.25rem 0;
      font-size: 0.9rem;
    }}
    footer {{
      text-align: center;
      font-size: 0.75rem;
      padding: 1rem 0 2rem;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <header role="banner">
    <h1>Relational Computer</h1>
    <p class="meta">Proof engine and graph for relational mathematics programs.</p>
    <nav aria-label="Primary navigation">
      <a href="/">Overview</a>
      <a href="/objects">Objects</a>
      <a href="/runbooks">Runbooks</a>
      <a href="/operators">Operators</a>
      <button class="theme-toggle" type="button" aria-label="Toggle color theme" onclick="window.toggleTheme && window.toggleTheme()">
        Theme
      </button>
    </nav>
  </header>
  <main>
    <h2>{title}</h2>
    {body}
  </main>
  <footer>
    Relational astrolabe — read-only view of canonical carriers, runbooks, and operators.
  </footer>
  <script>
    (function () {{
      var root = document.documentElement;
      var stored = null;
      try {{
        stored = window.localStorage.getItem("relationality-theme");
      }} catch (_) {{}}
      var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      var initial = stored || (prefersDark ? "dark" : "light");
      root.setAttribute("data-theme", initial);
      window.toggleTheme = function () {{
        var current = root.getAttribute("data-theme") || "dark";
        var next = current === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try {{
          window.localStorage.setItem("relationality-theme", next);
        }} catch (_) {{}}
      }};
    }})();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """
    Root UI entrypoint (alias of /ui).

    This is the human-oriented, read-only explorer surface. Programmatic
    clients should continue to use /api and /rdf directly.
    """
    return ui_index()


@app.get("/ui", response_class=HTMLResponse)
def ui_index() -> HTMLResponse:
    """
    Read-only web frontend index for exploring carriers and runbooks.
    """
    objects = COMPUTER.objects
    runbooks = COMPUTER.runbooks
    total_objects = len(objects.by_id)
    total_kinds = len(objects.by_kind)
    total_runbooks = len(runbooks.by_id)

    body = f"""
<section aria-labelledby="overview-nav">
  <h3 id="overview-nav" class="section-header">Explore</h3>
  <ul class="stacked-list">
    <li><a href="/objects">Objects</a> — all canonical carriers.</li>
    <li><a href="/runbooks">Runbooks</a> — operator composites.</li>
    <li><a href="/operators">Operators</a> — where each operator is used.</li>
  </ul>
</section>
<section aria-labelledby="overview-notes">
  <h3 id="overview-notes" class="section-header">Notes</h3>
  <p class="meta">
    This frontend is read-only; it reflects the canonical fixtures loaded from <code>data/objects</code>
    and <code>data/runbooks</code>. All IDs and payloads are already schema- and law-validated.
  </p>
  <p class="meta">
    Inventory: <strong>{total_objects}</strong> objects across <strong>{total_kinds}</strong> kinds ·
    <strong>{total_runbooks}</strong> runbooks.
  </p>
</section>
"""
    return _html_page("Relational Computer — Explorer", body)


@app.get("/ui/objects", response_class=HTMLResponse)
@app.get("/objects", response_class=HTMLResponse)
def ui_list_objects() -> HTMLResponse:
    objects = COMPUTER.objects
    by_kind: dict[str, list[dict]] = {}
    for obj in objects.by_id.values():
        by_kind.setdefault(obj.get("kind", "unknown"), []).append(obj)
    parts: list[str] = [
        '<section aria-labelledby="objects-by-kind">',
        '<h3 id="objects-by-kind" class="section-header">Objects by kind</h3>',
        "<ul class=\"stacked-list\">",
    ]
    for kind in sorted(by_kind.keys()):
        parts.append(f"<li><span class=\"badge\">{kind}</span><ul>")
        for obj in sorted(by_kind[kind], key=lambda o: o["id"]):
            oid = obj["id"]
            sig = _object_signature_bar(obj)
            parts.append(
                f'<li><a href="/objects/{oid}" aria-label="Object {oid}">{sig}</a></li>'
            )
        parts.append("</ul></li>")
    parts.append("</ul></section>")
    return _html_page("Objects", "\n".join(parts))


@app.get("/ui/objects/{object_id}", response_class=HTMLResponse)
@app.get("/objects/{object_id}", response_class=HTMLResponse)
def ui_get_object(object_id: str) -> HTMLResponse:
    import json

    objects = COMPUTER.objects
    obj = objects.by_id.get(object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"object {object_id} not found")
    kind = obj.get("kind", "unknown")

    # Discover relations for a more \"relational slide rule\" view.
    all_ids = set(objects.by_id.keys())
    id_to_kind: dict[str, str] = {oid: o.get("kind", "unknown") for oid, o in objects.by_id.items()}

    def _collect_referenced_ids(value: object, acc: set[str]) -> None:
        if isinstance(value, str) and value in all_ids:
            acc.add(value)
        elif isinstance(value, list):
            for item in value:
                _collect_referenced_ids(item, acc)
        elif isinstance(value, dict):
            for item in value.values():
                _collect_referenced_ids(item, acc)

    referenced: set[str] = set()
    _collect_referenced_ids(obj, referenced)
    referenced.discard(object_id)

    referenced_by: set[str] = set()
    for other_id, other in objects.by_id.items():
        if other_id == object_id:
            continue
        acc: set[str] = set()
        _collect_referenced_ids(other, acc)
        if object_id in acc:
            referenced_by.add(other_id)

    siblings: list[str] = []
    sibling_objs: dict[str, dict] = {}
    for sibling in objects.by_kind.get(kind, {}).values():
        sid = sibling["id"]
        if sid != object_id:
            siblings.append(sid)
            sibling_objs[sid] = sibling
    siblings.sort()

    # Pre-render relational HTML fragments with signatures.
    ref_fragments: list[str] = []
    for rid in sorted(referenced):
        ref_obj = objects.by_id.get(rid) or {"id": rid, "kind": id_to_kind.get(rid, "unknown")}
        sig = _object_signature_bar(ref_obj)
        ref_fragments.append(
            f'<a href="/objects/{rid}" aria-label="Object {rid}">{sig}</a>'
        )
    references_html = " ".join(ref_fragments) if ref_fragments else '<span class="meta">none</span>'

    ref_by_fragments: list[str] = []
    for rid in sorted(referenced_by):
        ref_obj = objects.by_id.get(rid) or {"id": rid, "kind": id_to_kind.get(rid, "unknown")}
        sig = _object_signature_bar(ref_obj)
        ref_by_fragments.append(
            f'<a href="/objects/{rid}" aria-label="Object {rid}">{sig}</a>'
        )
    referenced_by_html = " ".join(ref_by_fragments) if ref_by_fragments else '<span class="meta">none</span>'

    neighbor_fragments: list[str] = []
    for sid in siblings:
        sobj = sibling_objs.get(sid) or {"id": sid, "kind": kind}
        sig = _object_signature_bar(sobj)
        neighbor_fragments.append(
            f'<a href="/objects/{sid}" aria-label="Object {sid}">{sig}</a>'
        )
    neighbors_html = " ".join(neighbor_fragments) if neighbor_fragments else '<span class="meta">none</span>'

    sig = _object_signature_bar(obj)
    # Build a shallow relational map: center object + neighbors with
    # edges typed by operator families found in runbook steps.
    runbooks = load_runbooks()
    kind_op_index = _build_kind_operator_index(runbooks.by_id)
    relation_map = _object_relation_map(
        center=obj,
        referenced=referenced,
        referenced_by=referenced_by,
        objects_by_id=objects.by_id,
        kind_operator_index=kind_op_index,
    )
    json_payload = json.dumps(obj, indent=2, sort_keys=True)
    body = f"""
<section aria-labelledby="object-header">
  <h3 id="object-header" class="section-header">Object</h3>
  <p>{sig}</p>
  <p>{relation_map}</p>
</section>
<section aria-labelledby="object-meta">
  <h3 id="object-meta" class="section-header">Metadata</h3>
  <dl>
    <dt>ID</dt>
    <dd><code>{object_id}</code></dd>
    <dt>Kind</dt>
    <dd>{kind}</dd>
  </dl>
</section>
    <section aria-labelledby="object-relations">
      <h3 id="object-relations" class="section-header">Relations</h3>
      <dl>
        <dt>References</dt>
        <dd>
          {references_html}
        </dd>
        <dt>Referenced by</dt>
        <dd>
          {referenced_by_html}
        </dd>
      </dl>
    </section>
    <section aria-labelledby="object-neighborhood">
      <h3 id="object-neighborhood" class="section-header">Same-kind neighborhood</h3>
      <p class="meta">Other <code>{kind}</code> carriers:</p>
      <p>
        {neighbors_html}
      </p>
    </section>
<section aria-labelledby="object-json">
  <h3 id="object-json" class="section-header">Canonical payload</h3>
  <pre>{json_payload}</pre>
</section>
"""
    return _html_page("Object", body)


@app.get("/ui/runbooks", response_class=HTMLResponse)
@app.get("/runbooks", response_class=HTMLResponse)
def ui_list_runbooks() -> HTMLResponse:
    runbooks = COMPUTER.runbooks
    rbs = sorted(runbooks.by_id.values(), key=lambda rb: (rb.get("name", ""), rb["id"]))
    parts: list[str] = [
        '<section aria-labelledby="runbooks-list">',
        '<h3 id="runbooks-list" class="section-header">Runbooks</h3>',
        '<ul class="stacked-list">',
    ]
    for rb in rbs:
        rid = rb["id"]
        name = rb.get("name", "")
        label = f"{name}" if name else rid[:8]
        sig = _runbook_signature_bar(rb)
        parts.append(
            f'<li>{sig}<a href="/runbooks/{rid}">{label}</a></li>'
        )
    parts.append("</ul></section>")
    return _html_page("Runbooks", "\n".join(parts))


@app.get("/ui/runbooks/{runbook_id}", response_class=HTMLResponse)
@app.get("/runbooks/{runbook_id}", response_class=HTMLResponse)
def ui_get_runbook(runbook_id: str) -> HTMLResponse:
    import json

    runbooks = COMPUTER.runbooks
    rb = runbooks.by_id.get(runbook_id)
    if rb is None:
        raise HTTPException(status_code=404, detail=f"runbook {runbook_id} not found")
    steps = rb.get("steps", [])
    # Operator sequence track for quick scanning.
    ordered_steps = sorted(steps, key=lambda s: s.get("step_index", 0))
    op_seq: list[str] = [step.get("operator", "") for step in ordered_steps if step.get("operator")]
    sequence_html = ""
    if op_seq:
        sequence_html = " &#8594; ".join(
            f'<a href="/operators#{op}"><code>{op}</code></a>' for op in op_seq
        )
    else:
        sequence_html = '<span class="meta">no steps</span>'

    sig = _runbook_signature_bar(rb)
    ribbon = _runbook_ribbon(rb)
    step_lines: list[str] = ['<ul class="stacked-list">']
    for step in ordered_steps:
        op = step.get("operator")
        idx = step.get("step_index")
        step_lines.append(f"<li>Step {idx}: operator <code>{op}</code></li>")
    step_lines.append("</ul>")
    json_payload = json.dumps(rb, indent=2, sort_keys=True)
    body = f"""
<section aria-labelledby="runbook-header">
  <h3 id="runbook-header" class="section-header">Runbook</h3>
  <p>{sig}</p>
</section>
<section aria-labelledby="runbook-summary">
  <h3 id="runbook-summary" class="section-header">Summary</h3>
  <p class="meta">Runbook <code>{rb.get('name','')}</code> (<code>{runbook_id}</code>)</p>
</section>
<section aria-labelledby="runbook-sequence">
  <h3 id="runbook-sequence" class="section-header">Operator sequence</h3>
  <p>{ribbon}</p>
  <p class="meta">{sequence_html}</p>
</section>
<section aria-labelledby="runbook-steps">
  <h3 id="runbook-steps" class="section-header">Steps</h3>
  {''.join(step_lines)}
</section>
<section aria-labelledby="runbook-json">
  <h3 id="runbook-json" class="section-header">Canonical payload</h3>
  <pre>{json_payload}</pre>
</section>
"""
    return _html_page("Runbook", body)


@app.get("/ui/operators", response_class=HTMLResponse)
@app.get("/operators", response_class=HTMLResponse)
def ui_list_operators() -> HTMLResponse:
    runbooks = COMPUTER.runbooks
    usage: dict[str, list[str]] = {}
    for rb in runbooks.by_id.values():
        rid = rb["id"]
        for step in rb.get("steps", []):
            op = step.get("operator")
            if not isinstance(op, str):
                continue
            usage.setdefault(op, []).append(rid)
    if not usage:
        return _html_page("Operators", "<p class=\"meta\">No operators found in runbooks.</p>")
    parts: list[str] = [
        '<section aria-labelledby="operators-list">',
        '<h3 id="operators-list" class="section-header">Operators</h3>',
        '<ul class="stacked-list">',
    ]
    for op in sorted(usage.keys()):
        rids = sorted(set(usage[op]))
        links = " ".join(f'<a href="/runbooks/{rid}">{rid}</a>' for rid in rids)
        parts.append(
            f'<li id="{op}"><code>{op}</code> '
            f'<span class="meta">({len(rids)} runbook(s))</span> — {links}</li>'
        )
    parts.append("</ul></section>")
    return _html_page("Operators", "\n".join(parts))
