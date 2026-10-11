"""
FastAPI application factory for the RRPR interface.

Used by scripts/rrpr-web.py and pytest fixtures.
"""

from pathlib import Path
from fastapi import FastAPI

from rrpr.database import init_database
from rrpr.api import web, stats, git, query, graph, recognition, relation, metadata_discovery, entities


def create_app() -> FastAPI:
    app = FastAPI(
        title="RRPR Interface - Relationing Research Program Repository",
        description="Navigate and query the Relationing research repository as a knowledge graph",
        version="0.2.0"
    )

    @app.on_event("startup")
    async def startup() -> None:
        """Initialize database on startup if missing."""
        db_path = Path("data/databases/rsc.db")
        if not db_path.exists():
            init_database(db_path)

    # Concept-aligned routers
    app.include_router(recognition.router)
    app.include_router(relation.router)

    # Metadata discovery
    app.include_router(metadata_discovery.router)

    # Technical infrastructure routers
    app.include_router(web.router)
    app.include_router(stats.router)
    app.include_router(git.router)
    app.include_router(query.router)
    app.include_router(graph.router)

    # Legacy routers
    app.include_router(entities.router)

    return app


app = create_app()
