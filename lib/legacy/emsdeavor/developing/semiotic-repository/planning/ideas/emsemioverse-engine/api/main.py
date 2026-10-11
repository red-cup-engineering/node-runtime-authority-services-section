"""Emsemioverse Engine - FastAPI backend for skills and MCP."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from engine.api.app_state import AppState, create_app_state, shutdown_app_state
from engine.api.api_v1 import router as api_v1_router
from engine.api.logging_utils import request_logger
from engine.api.mcp_sdk_adapter import build_mcp_app
from engine.api.settings import settings
from engine.api.skill_runner import execute_skill_internal, run_skill

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager.

    Startup: load skill manifest.
    Shutdown: teardown in-memory state.
    """
    logger.info("Starting application...")

    state = await create_app_state()
    app.state.app_state = state

    if not state.is_ready:
        logger.error("Application startup failed: %s", state.startup_error)
        raise RuntimeError(f"Application startup failed: {state.startup_error}")

    logger.info("Application ready with %s skills", state.get_skill_count())

    def manifest_provider():
        return state.manifest

    def resource_lister(path: str = ""):
        skill = state.get_skill_by_id("list-directory-skill")
        if not skill:
            return []
        inputs = {"path": path or "."}
        result = run_skill(skill, inputs)
        if not result.success or not result.outputs:
            return []
        entries = result.outputs.get("entries", [])
        resources = []
        for entry in entries:
            resources.append(
                {
                    "path": entry.get("path"),
                    "name": entry.get("name") or entry.get("path"),
                    "description": None,
                    "mimeType": "application/x-directory" if entry.get("type") == "dir" else "text/plain",
                }
            )
        return resources

    def resource_reader(uri: str):
        if not uri.startswith("library://"):
            raise HTTPException(status_code=400, detail="Unsupported resource URI")
        path = uri.replace("library://", "", 1).lstrip("/")
        skill = state.get_skill_by_id("read-file-skill")
        if not skill:
            raise HTTPException(status_code=500, detail="read-file skill not available")
        result = run_skill(skill, {"path": path})
        if not result.success or not result.outputs:
            raise HTTPException(status_code=400, detail=result.error or "read failed")
        content = result.outputs.get("content", "")
        binary = result.outputs.get("binary", False)
        mime_type = "application/octet-stream" if binary else "text/plain"
        return {"uri": uri, "mimeType": mime_type, "text": content}

    def tool_executor(name: str, args: dict[str, Any]):
        return execute_skill_internal(name, args, state)

    mcp_app = build_mcp_app(
        manifest_provider=manifest_provider,
        resource_lister=resource_lister,
        resource_reader=resource_reader,
        tool_executor=tool_executor,
    )
    app.mount("/mcp", mcp_app)
    logger.info("Mounted MCP server via official SDK surface")

    yield

    logger.info("Shutting down application...")
    await shutdown_app_state(state)
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Emsemioverse API",
    description="API for interacting with the Emsemioverse library via skills.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(request_logger)

app.include_router(api_v1_router)


def get_app_state(request: Request) -> AppState:
    """Dependency to get application state.

    Raises 503 if application is not ready.
    """
    state = request.app.state.app_state
    if not state.is_ready:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {state.startup_error or 'Unknown error'}",
        )
    return state


@app.get("/health/live")
async def health_live():
    """Liveness probe - is the process running?"""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready(state: AppState = Depends(get_app_state)):
    """Readiness probe - is the application ready to serve requests?"""
    if not state.is_ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": state.startup_error or "Unknown error",
            },
        )

    return {
        "status": "ready",
        "skill_count": state.get_skill_count(),
    }


@app.get("/health")
async def health():
    """Simple health check for deployment - returns immediately."""
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
async def root(state: AppState = Depends(get_app_state)):
    """Minimal landing page."""
    skill_count = state.get_skill_count()
    return (
        "<html><body>"
        "<h1>Emsemioverse Engine</h1>"
        f"<p>Skills loaded: {skill_count}</p>"
        "<p>See <a href=\"/docs\">OpenAPI</a> for HTTP endpoints.</p>"
        "</body></html>"
    )


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Emsemioverse API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
