"""FastAPI middleware for policy enforcement.

Provides middleware and decorators for enforcing policies
on API requests.
"""

from __future__ import annotations

import json
from functools import wraps
from typing import Any, Callable, Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.schemas.policy import PolicyScope
from app.policy.engine import PolicyEngine, get_policy_engine


SCOPE_MAPPING = {
    "/api/tracepoints": PolicyScope.RECOGNITION,
    "/api/runbooks": PolicyScope.RUNBOOK,
    "/api/snapshots": PolicyScope.SNAPSHOT,
}


class PolicyMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces policies on requests."""
    
    def __init__(self, app, engine: Optional[PolicyEngine] = None):
        super().__init__(app)
        self.engine = engine or get_policy_engine()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through policy engine."""
        if request.method == "GET":
            return await call_next(request)
        
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)
        
        scope = self._get_scope_for_path(request.url.path)
        
        if scope:
            content_type = request.headers.get("content-type", "")
            
            if content_type.startswith("application/json"):
                try:
                    body = await request.body()
                    if body:
                        target = json.loads(body)
                        
                        result = self.engine.evaluate(
                            target=target if isinstance(target, dict) else {},
                            scope=scope,
                        )
                        
                        if not result.allowed:
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "detail": {
                                        "message": "Policy violation",
                                        "decision": result.to_dict(),
                                    }
                                }
                            )
                        
                        request.state.policy_decision = result
                except json.JSONDecodeError as e:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "detail": {
                                "message": "Invalid JSON in request body",
                                "error": str(e),
                            }
                        }
                    )
                except Exception as e:
                    return JSONResponse(
                        status_code=500,
                        content={
                            "detail": {
                                "message": "Policy evaluation error",
                                "error": str(e),
                            }
                        }
                    )
            elif content_type and not content_type.startswith("multipart/form-data"):
                result = self.engine.evaluate(
                    target={},
                    scope=scope,
                )
                
                if not result.allowed:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": {
                                "message": "Policy violation (non-JSON content)",
                                "decision": result.to_dict(),
                            }
                        }
                    )
                
                request.state.policy_decision = result
        
        response = await call_next(request)
        return response
    
    def _get_scope_for_path(self, path: str) -> Optional[PolicyScope]:
        """Determine the policy scope from the request path."""
        for prefix, scope in SCOPE_MAPPING.items():
            if path.startswith(prefix):
                return scope
        return None


def require_policy(
    policy_ids: list[str],
    scope: PolicyScope = PolicyScope.RECOGNITION,
) -> Callable:
    """Decorator to require specific policies for an endpoint.
    
    Usage:
        @app.post("/recognitions")
        @require_policy(["intake-policy"])
        async def create_recognition(data: dict):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            engine = get_policy_engine()
            
            data = kwargs.get("data", {})
            if not isinstance(data, dict):
                data = {}
            
            result = engine.evaluate(
                target=data,
                scope=scope,
                policy_ids=policy_ids,
            )
            
            if not result.allowed:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "message": "Policy violation",
                        "decision": result.to_dict(),
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_policy(
    target: dict[str, Any],
    policy_ids: Optional[list[str]] = None,
    scope: PolicyScope = PolicyScope.RECOGNITION,
    engine: Optional[PolicyEngine] = None,
) -> dict[str, Any]:
    """Check policies against a target without enforcing.
    
    Returns the policy decision result.
    """
    engine = engine or get_policy_engine()
    result = engine.evaluate(
        target=target,
        scope=scope,
        policy_ids=policy_ids,
    )
    return result.to_dict()
