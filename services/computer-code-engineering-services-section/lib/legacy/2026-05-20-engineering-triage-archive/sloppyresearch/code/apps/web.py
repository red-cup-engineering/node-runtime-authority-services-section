"""
Web interface for the Relationing Research Program Repository.

This is a thin bootstrap that registers modular API routers.
All endpoint logic is in code/library/api/*.

The repository is the research. This web interface helps navigate it.
"""

from fastapi import FastAPI
from pathlib import Path

from code.library.database import init_database
from code.library.api import web, stats, git, query, graph, recognition, relation, metadata_discovery
# Legacy entity router (being phased out - use recognition/relation instead)
from code.library.api import entities

app = FastAPI(
    title="RRPR Interface - Relationing Research Program Repository",
    description="Navigate and query the Relationing research repository as a knowledge graph",
    version="0.2.0"
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    db_path = Path("data/databases/rsc.db")
    if not db_path.exists():
        init_database(db_path)


# Register all modular routers

# Concept-aligned routers (embody Relationing theory)
app.include_router(recognition.router)
app.include_router(relation.router)

# Metadata discovery (makes theoretical foundations queryable)
app.include_router(metadata_discovery.router)

# Technical infrastructure routers
app.include_router(web.router)
app.include_router(stats.router)
app.include_router(git.router)
app.include_router(query.router)
app.include_router(graph.router)

# Legacy routers (maintain backwards compatibility)
app.include_router(entities.router)
