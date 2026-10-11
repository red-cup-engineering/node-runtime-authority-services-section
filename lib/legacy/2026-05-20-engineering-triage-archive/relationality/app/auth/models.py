"""User and session models for PostgreSQL."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model representing an authenticated user."""
    
    id: str = Field(..., description="Replit user ID (sub claim)")
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def display_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.email:
            return self.email.split("@")[0]
        return f"User {self.id[:8]}"


class AuthSession(BaseModel):
    """Session model for storing OAuth tokens."""
    
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    session_key: str
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserPublic(BaseModel):
    """Public user info for API responses."""
    
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    display_name: str
