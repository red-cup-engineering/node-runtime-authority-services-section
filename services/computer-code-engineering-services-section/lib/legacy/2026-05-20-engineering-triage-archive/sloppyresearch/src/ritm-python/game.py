"""
engine.py — Minimal "Relational-Cohesive" game engine skeleton

Builds directly on the user's modules:
- cell.py        : constructive presheaf cell (Y,R) + step/run
- category.py    : RelationalObject helper to snapshot (Y,R)
- geometry.py    : cohesive geometric reflection (to points/edges)
- physics.py     : simple field dynamics and time steppers
- analysis.py    : diagnostics (entropy, curvature, coherence)

Usage:
    python engine.py

This is intentionally tiny and readable; treat it as a starting point.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Dict

from cell import RelationalCell
from category import relational_object_from_YR
from geometry import GeometricCell, from_relational_object, visualize_ascii, BOX_GEO, DIAMOND_GEO, PI, NABLA, DELTA_GEO
from physics import (
    ScalarField, VectorField,
    spring_potential_gradient, semi_implicit_step,
    total_energy, pullback_scalar, pullback_vector
)
from analysis import summary as diag_summary


@dataclass
class EngineConfig:
    max_rule_steps: int = 64   # rule-system steps per tick (upper bound)
    dt: float = 0.1            # physics timestep
    mass: float = 1.0          # mass for semi-implicit update
    spring_k: float = 0.5      # spring stiffness for sample potential
    rest: float = 1.0          # rest-length scale for sample potential
    apply_functor_every: int = 0  # set >0 to sample cohesive functors periodically


class GameEngine:
    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self.cell = RelationalCell()  # seed one arrow (0->1)
        self.time = 0.0
        self.tick_count = 0

        # Initial geometric reflection + fields
        self.geom: GeometricCell = self._reflect()
        self.phi = ScalarField({n: 1.0 for n in self.geom.points})      # node "size"
        self.vel = VectorField({n: (0.1, 0.0) for n in self.geom.points})  # initial drift

        # Cohesive functor cycle (optional flavor transforms)
        self._functor_cycle = [PI, BOX_GEO, DIAMOND_GEO, NABLA, DELTA_GEO]
        self._functor_idx = 0

    # --- Core steps ----------------------------------------------------------

    def _stabilize_rules(self) -> None:
        """Apply constructive laws until stable or bound is reached."""
        for _ in range(self.config.max_rule_steps):
            if self.cell.step() is None:
                break

    def _reflect(self) -> GeometricCell:
        """Snapshot (Y,R) -> RelationalObject -> GeometricCell."""
        X = relational_object_from_YR(self.cell.Y, self.cell.R)
        return from_relational_object(X)

    def _maybe_apply_cohesive_functor(self) -> None:
        n = self.config.apply_functor_every
        if n and (self.tick_count % n == 0):
            F = self._functor_cycle[self._functor_idx]
            self.geom = F.map_obj(self.geom)
            # Pull fields onto the transformed chart
            self.geom, self.phi = pullback_scalar(F, self.geom, self.phi)
            self.geom, self.vel = pullback_vector(F, self.geom, self.vel)
            self._functor_idx = (self._functor_idx + 1) % len(self._functor_cycle)

    def _physics_step(self) -> None:
        """Semi-implicit position+velocity update under a springy edge potential."""
        gradU = lambda cell, phi: spring_potential_gradient(
            cell, phi, k=self.config.spring_k, rest=self.config.rest
        )
        self.geom, self.vel = semi_implicit_step(
            self.geom, self.vel, self.phi, gradU, dt=self.config.dt, mass=self.config.mass
        )

    # --- Public API ----------------------------------------------------------

    def tick(self) -> Dict[str, float]:
        """
        Advance the world by one tick:
          1) close under rules (C/RT/δ) with RC coupling
          2) reflect to geometry
          3) optional cohesive functor (flavor)
          4) physics update
          5) diagnostics
        """
        self._stabilize_rules()
        self.geom = self._reflect()
        self._maybe_apply_cohesive_functor()
        self._physics_step()
        self.time += self.config.dt
        self.tick_count += 1

        # Diagnostics
        diag = diag_summary(self.geom)
        energy = total_energy(self.geom, self.vel, self.phi)
        return {
            "time": self.time,
            "ticks": self.tick_count,
            "energy": energy,
            "nodes": len(self.geom.points),
            "edges": len(self.geom.edges),
            "diag_coherence": float(diag.splitlines()[-1].split("=")[-1]) if "Coherence index" in diag else 0.0,
        }

    def add_relation(self, a: Tuple[int,int], b: Tuple[int,int]) -> None:
        """Player/AI tool: add symmetric relation (a ∼ b)."""
        self.cell.R.setdefault(a, set()).add(b)
        self.cell.R.setdefault(b, set()).add(a)

    def add_edge(self, a: Tuple[int,int], b: Tuple[int,int]) -> None:
        """Level design tool: add directed arrow (a → b)."""
        self.cell.Y.setdefault(a, set()).add(b)

    # --- Helpers for demos ---------------------------------------------------

    def render_ascii(self) -> str:
        return visualize_ascii(self.geom)


def demo():
    cfg = EngineConfig(max_rule_steps=64, dt=0.1, apply_functor_every=0)
    eng = GameEngine(cfg)

    print("== Relational-Cohesive Engine (demo) ==")
    for t in range(10):
        stats = eng.tick()
        print(f"[{t:02d}] t={stats['time']:.2f}  nodes={stats['nodes']} edges={stats['edges']}  E={stats['energy']:.4f}")
        if t % 5 == 0:
            print(eng.render_ascii())
            print("---")

    # Example of a player action: relate two nodes to "imprint" connectivity
    # (IDs at level 0 are typically (nid, 0).)
    eng.add_relation((0,0), (1,0))
    stats = eng.tick()
    print("After adding relation (0,0) ∼ (1,0):")
    print(eng.render_ascii())
    print(f"Energy now: {stats['energy']:.4f}")


if __name__ == "__main__":
    demo()
