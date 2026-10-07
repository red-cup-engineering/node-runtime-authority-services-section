"""Realizer binding by operator family name."""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Callable, Dict

from relationality.errors import LoaderError


def resolve_realizer(operator: str) -> Callable:
    """Import relationality.realizers.<operator> and return the callable named like the operator."""
    module_name = f"relationality.realizers.{operator}"
    try:
        module: ModuleType = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise LoaderError(f"Missing realizer module for operator {operator}") from exc

    func = getattr(module, operator, None)
    if func is None or not callable(func):
        raise LoaderError(f"Realizer function {operator} not found in module {module_name}")
    if getattr(func, "__module__", None) != module.__name__:
        raise LoaderError(f"Realizer {operator} must be defined in {module_name}")
    return func


def resolve_all(runbook: dict) -> Dict[str, Callable]:
    """Resolve all operators in a runbook to callables."""
    resolved = {}
    for step in runbook.get("steps", []):
        op = step["operator"]
        if op not in resolved:
            resolved[op] = resolve_realizer(op)
    return resolved
