"""FastAPI dependencies for authentication."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from app.auth.models import User
from app.auth.database import get_auth_pool, UserRepository, SessionRepository


async def get_current_user(request: Request) -> Optional[User]:
    """Get the current authenticated user, or None if not authenticated.
    
    This dependency does not require authentication - it just provides
    the user if they are logged in.
    """
    session_key = request.cookies.get("session_id")
    
    if not session_key:
        return None
    
    try:
        pool = await get_auth_pool()
        session_repo = SessionRepository(pool)
        user_repo = UserRepository(pool)
        
        session = await session_repo.get_by_session_key(session_key)
        if not session:
            return None
        
        user = await user_repo.get(session.user_id)
        return user
    except Exception:
        return None


async def require_auth(request: Request) -> User:
    """Require an authenticated user.
    
    Raises 401 if not authenticated.
    """
    user = await get_current_user(request)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_required",
                "message": "You must be logged in to perform this action",
                "login_url": "/auth/login",
            },
        )
    
    return user
