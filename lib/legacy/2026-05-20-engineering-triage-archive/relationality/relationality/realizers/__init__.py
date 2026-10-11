"""
Realizer registry.

Each operator family corresponds to a module ``relationality.realizers.<name>``
exporting a single callable::

    realize(graph: RelationalGraph, inputs: Dict[str, dict], context: Dict[str, object]) -> RealizerOutput
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Callable, Dict, Protocol

if TYPE_CHECKING:  # pragma: no cover - type-checking only
    from relationality.realizer_output import RealizerOutput


class GraphLike(Protocol):  # pragma: no cover - typing aid only
    nodes: Dict[str, dict]
    edges: Dict[str, dict]


RealizerContext = Dict[str, object]
RealizerFn = Callable[[GraphLike, Dict[str, dict], RealizerContext], "RealizerOutput"]


def resolve_realizer(operator: str) -> RealizerFn:
    module_name = f"relationality.realizers.{operator}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise ImportError(f"realizer module {module_name} not found") from exc
    realizer = getattr(module, "realize", None)
    if realizer is None or not callable(realizer):
        raise ImportError(f"realizer module {module_name} lacks callable `realize`")
    return realizer  # type: ignore[return-value]


__all__ = ["RealizerFn", "RealizerContext", "resolve_realizer"]
