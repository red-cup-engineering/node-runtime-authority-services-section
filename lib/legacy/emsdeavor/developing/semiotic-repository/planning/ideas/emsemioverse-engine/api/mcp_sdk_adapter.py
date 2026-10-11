"""Adapter to host the MCP server using the official SDK."""

from __future__ import annotations

import logging
from typing import Any, Callable

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount

from mcp.server import Server as MCPServer
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import (
    CallToolResult,
    ListResourcesResult,
    ListToolsResult,
    Resource,
    TextContent,
    TextResourceContents,
    Tool,
)

logger = logging.getLogger(__name__)


def _inputs_to_schema(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert manifest inputs to a JSON schema object."""
    properties = {}
    required: list[str] = []
    type_map = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
    }
    for inp in inputs or []:
        name = inp.get("name")
        if not name:
            continue
        schema_type = type_map.get(str(inp.get("type", "string")), "string")
        prop: dict[str, Any] = {"type": schema_type}
        if inp.get("description"):
            prop["description"] = inp["description"]
        if "default" in inp:
            prop["default"] = inp["default"]
        properties[name] = prop
        if inp.get("required"):
            required.append(name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def build_mcp_app(
    *,
    manifest_provider: Callable[[], dict[str, Any]],
    resource_lister: Callable[[str], list[dict[str, Any]]],
    resource_reader: Callable[[str], dict[str, Any]],
    tool_executor: Callable[[str, dict[str, Any]], Any],
) -> Starlette:
    """Construct an ASGI app that serves MCP over Streamable HTTP."""
    server = MCPServer(name="Emsemioverse MCP", version="1.0.0")

    @server.list_tools()
    async def list_tools():
        manifest = manifest_provider() or {}
        skills = manifest.get("skills", [])
        tools = []
        for skill in skills:
            if not skill.get("runtime"):
                continue
            tool = Tool(
                name=skill.get("id"),
                description=skill.get("summary") or skill.get("description"),
                inputSchema=_inputs_to_schema(skill.get("inputs", [])),
                outputSchema=None,
            )
            tools.append(tool)
        return ListToolsResult(tools=tools)

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]):
        result = await tool_executor(name, arguments)
        content = []
        for item in result.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                content.append(TextContent(type="text", text=item.get("text", "")))
        is_error = bool(result.get("isError"))
        return CallToolResult(content=content, isError=is_error)

    @server.list_resources()
    async def list_resources():
        entries = resource_lister("")
        resources = []
        for entry in entries:
            resources.append(
                Resource(
                    name=entry.get("name") or entry.get("path"),
                    uri=entry.get("uri") or f"library://{entry.get('path')}",
                    description=entry.get("description"),
                    mimeType=entry.get("mimeType"),
                )
            )
        return ListResourcesResult(resources=resources)

    @server.read_resource()
    async def read_resource(uri: str):
        doc = resource_reader(uri)
        text = doc.get("text") or doc.get("content") or ""
        mime = doc.get("mimeType") or "text/plain"
        return {
            "contents": [
                TextResourceContents(uri=uri, text=text, mimeType=mime),
            ]
        }

    async def mcp_endpoint(scope, receive, send):
        path = scope.get("path", "")

        if path.endswith("/tools") or path.endswith("/message"):
            resp = Response('{"detail":"Not Found"}', status_code=404, media_type="application/json")
            await resp(scope, receive, send)
            return

        session_manager = StreamableHTTPSessionManager(server, json_response=True, stateless=True)
        async with session_manager.run():
            await session_manager.handle_request(scope, receive, send)

    mcp_app = Starlette(
        routes=[Mount("/", app=mcp_endpoint)],
    )
    return mcp_app
