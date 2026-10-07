from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set


@dataclass
class IdentityGroupoid:
    rep_for: Dict[str, str] = field(default_factory=dict)
    classes: Dict[str, Set[str]] = field(default_factory=dict)

    @classmethod
    def from_same_as(cls, mapping: Dict[str, Iterable[str]]):
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra == rb:
                return
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

        for k, vals in mapping.items():
            for v in vals:
                union(k, v)

        rep_for: Dict[str, str] = {}
        classes: Dict[str, Set[str]] = {}
        for x in list(parent.keys()):
            rep = find(x)
            rep_for[x] = rep
            classes.setdefault(rep, set()).add(x)
        return cls(rep_for=rep_for, classes=classes)

    def representative(self, const: str) -> str:
        return self.rep_for.get(const, const)

    def transport(self, const: str) -> str:
        return self.representative(const)

    def equivalents(self, const: str) -> List[str]:
        rep = self.representative(const)
        return sorted(self.classes.get(rep, {const}))
