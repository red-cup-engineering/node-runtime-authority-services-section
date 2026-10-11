from __future__ import annotations

"""
Universe publishing: render universes into external views.

This module takes an evaluated `Universe` and exports it to various
representations (HTML, JSON, RDF, OpenAPI, Pandoc). It is consciously
separate from how universes are *loaded* (e.g. from markdown).
"""

from .exporters import (  # re-export the concrete publishers
    default_targets_for_mode,
    export_all,
    export_html,
    export_json_api,
    export_openapi,
    export_pandoc,
    export_rdf,
    normalize_targets,
)

__all__ = [
    "export_all",
    "export_html",
    "export_json_api",
    "export_rdf",
    "export_openapi",
    "export_pandoc",
    "default_targets_for_mode",
    "normalize_targets",
]

