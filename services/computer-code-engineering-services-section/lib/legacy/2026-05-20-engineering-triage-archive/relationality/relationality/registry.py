"""
Realizer registry and dynamic binding (Section 7.3 of the README).

Realizers are bound once at boot from persistent metadata and importlib lookups.
"""

from __future__ import annotations

import importlib
from typing import Callable, Dict, List, Tuple

from .models import RealizerSpec

RealizerFn = Callable[..., object]


class RealizerRegistry:
    def __init__(self, specs: List[RealizerSpec]) -> None:
        self.specs = {spec.id: spec for spec in specs}
        self.callables: Dict[str, RealizerFn] = {}

    def bind_all(self) -> None:
        for spec in self.specs.values():
            module = importlib.import_module(spec.module)
            try:
                fn = getattr(module, spec.callable)
            except AttributeError as exc:
                raise ImportError(f"Callable {spec.callable} not found in {spec.module}") from exc
            self.callables[spec.id] = fn

    def get(self, realizer_id: str) -> Tuple[RealizerSpec, RealizerFn]:
        if realizer_id not in self.specs:
            raise KeyError(f"Realizer not registered: {realizer_id}")
        if realizer_id not in self.callables:
            raise KeyError(f"Realizer not bound: {realizer_id}")
        return self.specs[realizer_id], self.callables[realizer_id]
