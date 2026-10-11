"""Authentication middleware for protecting write endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.auth.database import get_auth_pool, UserRepository, SessionRepository


PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

PUBLIC_WRITE_PATHS = {
    "/auth/",
    "/docs",
    "/openapi",
    "/redoc",
    "/api/runbooks/validate",
    "/api/policies/check",
    "/api/intake/validate",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that requires authentication for write operations."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in PROTECTED_METHODS:
            return await call_next(request)
        
        path = request.url.path
        for public_path in PUBLIC_WRITE_PATHS:
            if path.startswith(public_path):
                return await call_next(request)
        
        session_key = request.cookies.get("session_id")
        
        if not session_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "error": "authentication_required",
                        "message": "Authentication required for write operations",
                        "login_url": "/auth/login",
                    }
                },
            )
        
        try:
            pool = await get_auth_pool()
            session_repo = SessionRepository(pool)
            user_repo = UserRepository(pool)
            
            session = await session_repo.get_by_session_key(session_key)
            if not session:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": {
                            "error": "session_expired",
                            "message": "Your session has expired. Please log in again.",
                            "login_url": "/auth/login",
                        }
                    },
                )
            
            user = await user_repo.get(session.user_id)
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": {
                            "error": "user_not_found",
                            "message": "User not found. Please log in again.",
                            "login_url": "/auth/login",
                        }
                    },
                )
            
            request.state.user = user
            request.state.session = session
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "detail": {
                        "error": "auth_error",
                        "message": f"Authentication error: {str(e)}",
                    }
                },
            )
        
        return await call_next(request)
