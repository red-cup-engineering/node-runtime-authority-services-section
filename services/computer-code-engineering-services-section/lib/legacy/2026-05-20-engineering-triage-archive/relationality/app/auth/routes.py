"""Authentication routes for OAuth flow."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from app.auth.models import User, AuthSession, UserPublic
from app.auth.database import get_auth_pool, UserRepository, SessionRepository
from app.auth.oauth import get_oauth_client, ISSUER_URL

auth_router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE_NAME = "session_id"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


async def get_session_key(request: Request) -> Optional[str]:
    """Get session key from cookie."""
    return request.cookies.get(SESSION_COOKIE_NAME)


async def set_session_cookie(response: Response, session_key: str):
    """Set the session cookie."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_key,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )


async def clear_session_cookie(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(key=SESSION_COOKIE_NAME)


@auth_router.get("/login")
async def login(request: Request, next: Optional[str] = None):
    """Start the OAuth login flow."""
    oauth = get_oauth_client()
    replit_client = oauth.create_client("replit")
    
    redirect_uri = str(request.url_for("auth_callback"))
    
    if next:
        request.session["next_url"] = next
    
    return await replit_client.authorize_redirect(
        request,
        redirect_uri,
        prompt="login consent",
    )


@auth_router.get("/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback."""
    try:
        oauth = get_oauth_client()
        replit_client = oauth.create_client("replit")
        token = await replit_client.authorize_access_token(request)
    except Exception as e:
        return RedirectResponse(url="/auth/error?message=" + str(e))
    
    id_token = token.get("id_token")
    if not id_token:
        return RedirectResponse(url="/auth/error?message=No+ID+token+received")
    
    try:
        user_claims = jwt.decode(id_token, options={"verify_signature": False})
    except Exception as e:
        return RedirectResponse(url="/auth/error?message=Invalid+ID+token")
    
    pool = await get_auth_pool()
    user_repo = UserRepository(pool)
    session_repo = SessionRepository(pool)
    
    user = User(
        id=str(user_claims["sub"]),
        email=user_claims.get("email"),
        first_name=user_claims.get("first_name"),
        last_name=user_claims.get("last_name"),
        profile_image_url=user_claims.get("profile_image_url"),
    )
    await user_repo.upsert(user)
    
    session_key = secrets.token_urlsafe(32)
    expires_at = None
    if token.get("expires_in"):
        expires_at = datetime.utcnow() + timedelta(seconds=token["expires_in"])
    
    session = AuthSession(
        user_id=user.id,
        session_key=session_key,
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        id_token=id_token,
        expires_at=expires_at,
    )
    await session_repo.create(session)
    
    next_url = request.session.pop("next_url", None) or "/"
    
    response = RedirectResponse(url=next_url)
    await set_session_cookie(response, session_key)
    
    return response


@auth_router.get("/logout")
async def logout(request: Request):
    """Log out the user."""
    session_key = await get_session_key(request)
    
    if session_key:
        pool = await get_auth_pool()
        session_repo = SessionRepository(pool)
        await session_repo.delete(session_key)
    
    repl_id = os.environ.get("REPL_ID", "")
    root_url = str(request.base_url).rstrip("/")
    
    end_session_url = f"{ISSUER_URL}/session/end"
    params = urlencode({
        "client_id": repl_id,
        "post_logout_redirect_uri": root_url,
    })
    logout_url = f"{end_session_url}?{params}"
    
    response = RedirectResponse(url=logout_url)
    await clear_session_cookie(response)
    
    return response


@auth_router.get("/me")
async def get_current_user_info(request: Request) -> dict:
    """Get the current authenticated user."""
    session_key = await get_session_key(request)
    
    if not session_key:
        return {"authenticated": False, "user": None}
    
    pool = await get_auth_pool()
    session_repo = SessionRepository(pool)
    user_repo = UserRepository(pool)
    
    session = await session_repo.get_by_session_key(session_key)
    if not session:
        return {"authenticated": False, "user": None}
    
    user = await user_repo.get(session.user_id)
    if not user:
        return {"authenticated": False, "user": None}
    
    return {
        "authenticated": True,
        "user": UserPublic(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image_url=user.profile_image_url,
            display_name=user.display_name,
        ).model_dump(),
    }


@auth_router.get("/error")
async def auth_error(message: str = "Authentication failed"):
    """Display auth error."""
    return JSONResponse(
        status_code=401,
        content={"error": "authentication_failed", "message": message},
    )
