"""Versioned REST API surface for Emsemioverse skills."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from engine.api.app_state import AppState
from engine.api.skill_runner import SkillExecutionRequest, SkillExecutionResponse, run_skill

router = APIRouter(prefix="/api/v1", tags=["api-v1"])


@router.get("/health", tags=["health"])
async def health(request: Request):
    """Lightweight health check for liveness/readiness."""
    state = getattr(request.app.state, "app_state", None)
    ok = bool(state and state.is_ready)
    return {"ok": ok, "skills": state.get_skill_count() if state else 0}


class APIError(BaseModel):
    """Standard API error envelope."""

    code: str
    message: str
    detail: Optional[Any] = None


class SkillSummary(BaseModel):
    """Compact skill description."""

    id: str
    name: Optional[str] = None
    summary: Optional[str] = None
    kind: Optional[str] = None
    path: Optional[str] = None


class SkillListResponse(BaseModel):
    """Response for skill listing."""

    total: int
    skills: list[SkillSummary]


def get_app_state(request: Request) -> AppState:
    """Dependency to get application state for v1 API."""
    state = request.app.state.app_state
    if not state.is_ready:
        raise HTTPException(
            status_code=503,
            detail=APIError(
                code="service_unavailable",
                message=state.startup_error or "Service not ready",
            ).model_dump(),
        )
    return state


@router.get(
    "/skills",
    response_model=SkillListResponse,
    responses={404: {"model": APIError}},
)
async def list_skills_v1(
    request: Request,
    state: AppState = Depends(get_app_state),
    kind: str | None = Query(None, description="Filter by skill kind"),
):
    """List available skills with optional filters."""
    skills = state.get_skills()

    if kind:
        skills = [s for s in skills if s.get("kind") == kind]

    summaries = [
        SkillSummary(
            id=s.get("id", ""),
            name=s.get("name"),
            summary=s.get("summary"),
            kind=s.get("kind"),
            path=s.get("path"),
        )
        for s in skills
    ]

    return SkillListResponse(total=len(summaries), skills=summaries)


@router.get(
    "/skills/{skill_id}",
    responses={404: {"model": APIError}},
)
async def get_skill_v1(
    skill_id: str,
    request: Request,
    state: AppState = Depends(get_app_state),
):
    """Get details for a specific skill."""
    skill = state.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=APIError(code="skill_not_found", message=f"Skill not found: {skill_id}").model_dump(),
        )
    return skill


@router.post(
    "/skills/{skill_id}/execute",
    response_model=SkillExecutionResponse,
    responses={
        400: {"model": APIError},
        404: {"model": APIError},
        500: {"model": APIError},
    },
)
async def execute_skill_v1(
    skill_id: str,
    request: SkillExecutionRequest,
    state: AppState = Depends(get_app_state),
):
    """Execute a skill with the given inputs."""
    skill = state.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=APIError(code="skill_not_found", message=f"Skill not found: {skill_id}").model_dump(),
        )
    try:
        return run_skill(skill, request.inputs)
    except HTTPException as exc:
        detail = exc.detail
        if not isinstance(detail, dict):
            detail = APIError(code="skill_error", message=str(detail)).model_dump()
        raise HTTPException(status_code=exc.status_code, detail=detail)
    except Exception as exc:  # pragma: no cover - safeguard
        raise HTTPException(
            status_code=500,
            detail=APIError(code="skill_error", message=str(exc)).model_dump(),
        )
