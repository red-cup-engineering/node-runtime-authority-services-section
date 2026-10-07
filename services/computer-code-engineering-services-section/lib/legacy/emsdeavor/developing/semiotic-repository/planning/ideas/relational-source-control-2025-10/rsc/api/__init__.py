"""
API routers for the RRPR Interface.

This package contains modular FastAPI routers organized by Relationing concepts:

Concept-Aligned Routers (embody research theory):
- recognition: Recognized entities (documents, terms, authors)
- relation: Relational edges (citations, authorship, contributions)

Technical Infrastructure Routers:
- web: HTML UI endpoints
- stats: Database statistics
- git: Git-specific operations (files, commits, branches)
- query: Graph traversal operations
- graph: Complete graph export

Legacy Routers (being phased out):
- entities: Original REST-style entity endpoints (use recognition/relation instead)
"""

from fastapi import APIRouter

__all__ = ["web", "stats", "entities", "git", "query", "graph", "recognition", "relation", "metadata_discovery"]
