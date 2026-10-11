"""PostgreSQL database connection and schema for auth."""

from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

import asyncpg

from app.auth.models import User, AuthSession


AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    profile_image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_key TEXT NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    id_token TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_session_key ON auth_sessions(session_key);
"""


_pool: Optional[asyncpg.Pool] = None


async def get_auth_pool() -> asyncpg.Pool:
    """Get or create the auth database connection pool."""
    global _pool
    if _pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable not set")
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        async with _pool.acquire() as conn:
            await conn.execute(AUTH_SCHEMA)
    return _pool


async def close_auth_pool():
    """Close the database pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def upsert(self, user: User) -> User:
        """Create or update a user."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, first_name, last_name, profile_image_url, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    profile_image_url = EXCLUDED.profile_image_url,
                    updated_at = EXCLUDED.updated_at
                """,
                user.id,
                user.email,
                user.first_name,
                user.last_name,
                user.profile_image_url,
                user.created_at,
                datetime.utcnow(),
            )
        return user
    
    async def get(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            if not row:
                return None
            return User(
                id=row["id"],
                email=row["email"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                profile_image_url=row["profile_image_url"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


class SessionRepository:
    """Repository for session operations."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def create(self, session: AuthSession) -> AuthSession:
        """Create a new session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO auth_sessions (id, user_id, session_key, access_token, refresh_token, id_token, expires_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (session_key) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    id_token = EXCLUDED.id_token,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = EXCLUDED.updated_at
                """,
                session.id,
                session.user_id,
                session.session_key,
                session.access_token,
                session.refresh_token,
                session.id_token,
                session.expires_at,
                session.created_at,
                datetime.utcnow(),
            )
        return session
    
    async def get_by_session_key(self, session_key: str) -> Optional[AuthSession]:
        """Get a session by session key."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM auth_sessions WHERE session_key = $1",
                session_key
            )
            if not row:
                return None
            return AuthSession(
                id=row["id"],
                user_id=row["user_id"],
                session_key=row["session_key"],
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                id_token=row["id_token"],
                expires_at=row["expires_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
    
    async def delete(self, session_key: str) -> bool:
        """Delete a session."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM auth_sessions WHERE session_key = $1",
                session_key
            )
            return "DELETE 1" in result
    
    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM auth_sessions WHERE user_id = $1",
                user_id
            )
            count = int(result.split()[-1]) if result else 0
            return count
