"""OAuth client configuration for Replit OIDC."""

from __future__ import annotations

import os
from typing import Optional

from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError


ISSUER_URL = os.environ.get("ISSUER_URL", "https://replit.com/oidc")


def get_replit_oauth() -> OAuth:
    """Create and configure the Replit OAuth client."""
    repl_id = os.environ.get("REPL_ID")
    if not repl_id:
        raise RuntimeError("REPL_ID environment variable not set")
    
    oauth = OAuth()
    
    oauth.register(
        name="replit",
        client_id=repl_id,
        client_secret=None,
        server_metadata_url=f"{ISSUER_URL}/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid profile email offline_access",
            "code_challenge_method": "S256",
        },
    )
    
    return oauth


_oauth_client: Optional[OAuth] = None


def get_oauth_client() -> OAuth:
    """Get the singleton OAuth client."""
    global _oauth_client
    if _oauth_client is None:
        _oauth_client = get_replit_oauth()
    return _oauth_client
