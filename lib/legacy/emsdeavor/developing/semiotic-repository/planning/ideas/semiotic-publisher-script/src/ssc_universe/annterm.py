from __future__ import annotations

import dataclasses
from typing import Any, Iterable, List, Tuple


@dataclasses.dataclass
class ProvenanceStep:
    kind: str
    detail: str
    inputs: Tuple[str, ...] = dataclasses.field(default_factory=tuple)


@dataclasses.dataclass
class ProvenanceHistory:
    steps: List[ProvenanceStep]

    @classmethod
    def singleton(cls, kind: str, detail: str, inputs: Iterable[str] | None = None) -> "ProvenanceHistory":
        return cls(steps=[ProvenanceStep(kind=kind, detail=detail, inputs=tuple(inputs or ()))])

    def extend(self, step: ProvenanceStep) -> "ProvenanceHistory":
        return ProvenanceHistory(steps=self.steps + [step])

    def is_refinement_of(self, other: "ProvenanceHistory") -> bool:
        # simple subsequence check
        other_steps = other.steps
        if len(other_steps) > len(self.steps):
            return False
        i = 0
        for step in self.steps:
            if i < len(other_steps) and step == other_steps[i]:
                i += 1
        return i == len(other_steps)


class AnnTerm:
    raw: Any

    def interpret(self, transport) -> Tuple[Any, ProvenanceHistory]:
        raise NotImplementedError

    def surface(self) -> Any:
        return self.raw


@dataclasses.dataclass
class AtomTerm(AnnTerm):
    name: str
    raw: Any

    def interpret(self, transport) -> Tuple[Any, ProvenanceHistory]:
        return ("atom", self.name), ProvenanceHistory.singleton("interpret", f"atom:{self.name}")


@dataclasses.dataclass
class KeyValTerm(AnnTerm):
    key: str
    value: Any
    raw: Any

    def interpret(self, transport) -> Tuple[Any, ProvenanceHistory]:
        return ("keyval", self.key, self.value), ProvenanceHistory.singleton("interpret", f"key:{self.key}")


@dataclasses.dataclass
class RefTerm(AnnTerm):
    target: str
    raw: Any

    def interpret(self, transport) -> Tuple[Any, ProvenanceHistory]:
        rep = transport(self.target)
        prov = ProvenanceHistory.singleton("interpret", f"ref:{self.target}")
        if rep != self.target:
            prov = prov.extend(ProvenanceStep(kind="transport", detail=f"{self.target}->{rep}"))
        return ("ref", rep), prov


@dataclasses.dataclass
class FailureTerm(AnnTerm):
    reason: str
    raw: Any

    def interpret(self, transport) -> Tuple[Any, ProvenanceHistory]:
        return ("fail", self.reason), ProvenanceHistory.singleton("fail", self.reason)


FAIL_BOTTOM = "⊥_fail"


def parse_ann_term(obj: Any) -> AnnTerm:
    if isinstance(obj, str):
        if obj.strip().startswith("{") and obj.strip().endswith("}"):
            return FailureTerm(reason="unparseable", raw=obj)
        if obj.startswith("ref:[[") and obj.endswith("]]"):
            inner = obj[len("ref:[[") : -2]
            return RefTerm(target=inner, raw=obj)
        if ":" in obj:
            # interpret leading token as atom
            return AtomTerm(name=obj, raw=obj)
        return AtomTerm(name=obj, raw=obj)
    if isinstance(obj, dict):
        if "ref" in obj:
            return RefTerm(target=str(obj["ref"]), raw=obj)
        if "key" in obj and "value" in obj:
            return KeyValTerm(key=str(obj["key"]), value=obj["value"], raw=obj)
    return FailureTerm(reason="unparseable", raw=obj)
