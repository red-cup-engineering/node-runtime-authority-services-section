"""
engine_rel2d.py — A triangle-free, coordinate-free 2D engine prototype

Principle:
  - Treat "space" as relations, not coordinates.
  - Movement = composing arrows (Y).
  - Interaction/binding = symmetric relations (R).
  - Gameplay flow emerges from categorical laws (C, RT, RC, δ) and field diffusion.

Depends on your modules (same folder):
  - cell.py        : RelationalCell with step() / run()
  - category.py    : relational_object_from_YR (for clean snapshots)
  - analysis.py    : summary() for telemetry / curvature / coherence

This prototype avoids geometry and physics positions entirely.
It simulates a scalar "heat/influence" field diffusing along the
symmetrized topology (Y ∪ Yᵗ ∪ R).

Usage:
  python engine_rel2d.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, Set, Iterable, Optional, List

from cell import RelationalCell         # your constructive presheaf cell
from category import relational_object_from_YR  # snapshot helper
from analysis import summary as analysis_summary

Node = Tuple[int, int]  # (id, level)


# ----------------------------- Utilities -------------------------------------

def sym_neighbors(Y: Dict[Node, Set[Node]], R: Dict[Node, Set[Node]]) -> Dict[Node, Set[Node]]:
    """
    Undirected neighborhood used for diffusion and LOS-like logic.
    - From Y: treat every directed edge a->b as undirected neighbors {a,b}
    - From R: already symmetric
    """
    N: Dict[Node, Set[Node]] = {}
    def add(u: Node, v: Node):
        N.setdefault(u, set()).add(v)
        N.setdefault(v, set()).add(u)

    for a, outs in Y.items():
        for b in outs:
            add(a, b)
    for a, peers in R.items():
        for b in peers:
            add(a, b)
    return N


def node_degree(nbrs: Dict[Node, Set[Node]]) -> Dict[Node, int]:
    return {n: len(peers) for n, peers in nbrs.items()}


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else (hi if x > hi else x)


# ---------------------------- Engine core -------------------------------------

@dataclass
class Rel2DConfig:
    max_rule_steps: int = 64    # close categorical laws up to this many step() attempts
    dt: float = 0.25            # diffusion step
    diffusion: float = 0.35     # amount of topological diffusion per dt
    decay: float = 0.02         # global decay for stability
    heat_inject: float = 0.35   # "input" heat when player moves or interacts
    hud_recent_events: int = 6  # tail of event log to render


class Rel2DEngine:
    """
    Coordinate-free, triangle-free 2D engine.
    - World: (Y, R) inside RelationalCell
    - Field: scalar "heat/influence" on nodes
    - Actions: move (add edge), interact (add relation), lift (delta)
    - Tick: close rules -> snapshot -> diffuse heat -> compute telemetry
    """

    def __init__(self, cfg: Optional[Rel2DConfig] = None):
        self.cfg = cfg or Rel2DConfig()
        self.cell = RelationalCell()  # seeds a minimal arrow ((0,0)->(1,0)) by default
        self.heat: Dict[Node, float] = {}  # scalar field on nodes
        self.events: List[str] = []

        # A designated "player" node; in this toy, pick (0,0)
        self.player: Node = (0, 0)

        # Initialize field on seen nodes
        self._ensure_nodes_initialized()

    # ---- internals ----

    def _ensure_nodes_initialized(self):
        # Make sure heat exists for all nodes we currently know about
        for n in self._all_nodes():
            self.heat.setdefault(n, 0.0)

    def _all_nodes(self) -> Iterable[Node]:
        # Nodes appear as keys or targets in Y plus keys/peers in R
        Y, R = self.cell.Y, self.cell.R
        nodes: Set[Node] = set(Y.keys()) | set(R.keys())
        for a, outs in Y.items():
            nodes.add(a)
            nodes.update(outs)
        for a, peers in R.items():
            nodes.add(a)
            nodes.update(peers)
        return nodes

    def _stabilize_rules(self):
        # Run the constructive closure up to a bound
        for _ in range(self.cfg.max_rule_steps):
            if self.cell.step() is None:
                break

    def _diffuse_heat(self):
        """
        Simple topological diffusion:
          h_new(n) = h(n)*(1 - decay - diffusion) + diffusion * mean(h(neighbors))
        on the symmetrized neighborhood (Y ∪ Yᵗ ∪ R).
        """
        N = sym_neighbors(self.cell.Y, self.cell.R)
        if not N:
            return

        beta = self.cfg.diffusion
        decay = self.cfg.decay
        nxt: Dict[Node, float] = dict(self.heat)

        for n in self._all_nodes():
            peers = N.get(n, set())
            if peers:
                avg = sum(self.heat.get(p, 0.0) for p in peers) / len(peers)
            else:
                avg = self.heat.get(n, 0.0)
            nxt[n] = clamp(self.heat.get(n, 0.0) * (1.0 - decay - beta) + beta * avg)
        self.heat = nxt

    def _inject_heat(self, n: Node, amount: float):
        self.heat[n] = clamp(self.heat.get(n, 0.0) + amount)

    # ---- public API (actions) ----

    def move(self, target: Node):
        """
        Movement as arrow composition: add directed edge (player -> target).
        Laws (RT / RC) will propagate consequences on tick.
        """
        self.cell.Y.setdefault(self.player, set()).add(target)
        self.events.append(f"move: {self.player} -> {target}")
        self._inject_heat(target, self.cfg.heat_inject)

    def interact(self, obj: Node):
        """
        Interaction/binding as symmetric relation (player ∼ obj).
        """
        self.cell.R.setdefault(self.player, set()).add(obj)
        self.cell.R.setdefault(obj, set()).add(self.player)
        self.events.append(f"interact: {self.player} ∼ {obj}")
        self._inject_heat(obj, self.cfg.heat_inject)

    def lift(self, n: Node):
        """
        δ-lift: raise the node to the next layer (id, level+1).
        This demonstrates layered maps without coordinates.
        """
        (i, k) = n
        lifted = (i, k + 1)
        # Keep existing local structure through a portable link
        self.cell.Y.setdefault(n, set()).add(lifted)
        self.events.append(f"lift: {n} -> {lifted}")
        self._inject_heat(lifted, self.cfg.heat_inject)

    # ---- simulation step ----

    def tick(self) -> Dict[str, float]:
        """
        1) Close categorical laws up to stability/bound.
        2) Snapshot for telemetry.
        3) Diffuse topological heat.
        4) Return summary stats.
        """
        self._ensure_nodes_initialized()
        self._stabilize_rules()

        # Optional: take a clean snapshot (no geometry used, but handy for analysis)
        _X = relational_object_from_YR(self.cell.Y, self.cell.R)

        # Field diffusion (coordinate-free)
        self._diffuse_heat()

        # Telemetry
        report = self.telemetry()
        return report

    # ---- telemetry & rendering ----

    def telemetry(self) -> Dict[str, float]:
        # Use your analysis tools to compute curvature/coherence/χ on the graph
        # (analysis.summary expects a geometric cell in your stack;
        # here we simply reuse it as a generic graph summary by feeding Y/R through the snapshot.)
        # We’ll still call analysis.summary via relational snapshot for consistent metrics.
        try:
            diag_text = analysis_summary(relational_object_from_YR(self.cell.Y, self.cell.R))
        except Exception:
            # Fallback: minimal diagnostics if analysis expects geometry-specific structures
            diag_text = "Analysis unavailable"

        N = sym_neighbors(self.cell.Y, self.cell.R)
        deg = node_degree(N)
        num_nodes = len(set(self._all_nodes()))
        num_edges = sum(len(v) for v in self.cell.Y.values())
        num_rel = sum(len(v) for v in self.cell.R.values()) // 2  # symmetric count

        # crude "coherence" estimate from degrees: high variance -> low coherence
        if deg:
            dvals = list(deg.values())
            mean_d = sum(dvals) / len(dvals)
            var_d = sum((x - mean_d) ** 2 for x in dvals) / len(dvals)
            coh = 1.0 / (1.0 + var_d)
        else:
            coh = 1.0

        return {
            "nodes": float(num_nodes),
            "edges": float(num_edges),
            "relations": float(num_rel),
            "avg_degree": float(sum(deg.values()) / len(deg) if deg else 0.0),
            "coherence_est": float(coh),
            "heat_total": float(sum(self.heat.get(n, 0.0) for n in self._all_nodes())),
        }

    def render_ascii(self) -> str:
        """
        Render a purely topological view:
          - list nodes grouped by level
          - show outgoing edges and symmetric relations
          - show a heat bar (0..1) using blocks
        """
        # Group by level
        levels: Dict[int, List[Node]] = {}
        for n in sorted(self._all_nodes()):
            levels.setdefault(n[1], []).append(n)

        def heat_bar(x: float, width: int = 10) -> str:
            filled = int(round(clamp(x) * width))
            return "█" * filled + "·" * (width - filled)

        lines: List[str] = []
        lines.append("=== Rel2D (triangle-free) ===")
        # Recent events
        if self.events:
            tail = self.events[-self.cfg.hud_recent_events:]
            lines.append("events: " + " | ".join(tail))

        lines.append("")
        lines.append("NODES (by level):")
        for lvl in sorted(levels.keys()):
            rows = []
            for n in levels[lvl]:
                tag = "P" if n == self.player else " "
                rows.append(f"{tag}{n} h={self.heat.get(n,0):.2f} [{heat_bar(self.heat.get(n,0.0), 8)}]")
            lines.append(f"  level {lvl}: " + ",  ".join(rows))

        # Edges and relations
        lines.append("")
        lines.append("EDGES (directed a->b):")
        for a, outs in self.cell.Y.items():
            if not outs: continue
            outs_s = ", ".join(str(b) for b in sorted(outs))
            lines.append(f"  {a} -> {outs_s}")

        lines.append("")
        lines.append("RELATIONS (symmetric a~b):")
        seen = set()
        for a, peers in self.cell.R.items():
            for b in peers:
                key = tuple(sorted([a, b]))
                if key in seen: continue
                seen.add(key)
                lines.append(f"  {a} ∼ {b}")

        # Summary
        t = self.telemetry()
        lines.append("")
        lines.append(f"stats: nodes={int(t['nodes'])} edges={int(t['edges'])} rels={int(t['relations'])} "
                     f"avg_deg={t['avg_degree']:.2f} coherence≈{t['coherence_est']:.3f} heat_total={t['heat_total']:.2f}")
        return "\n".join(lines)


# ----------------------------- Demo ------------------------------------------

def demo():
    eng = Rel2DEngine()

    print("== Coordinate-free, triangle-free 2D engine demo ==")
    print(eng.render_ascii())
    print("--- tick ---")
    eng.tick()
    print(eng.render_ascii())

    # Player "moves" by composing an arrow to (1,0)
    eng.move((1, 0))
    eng.tick()
    print("--- after move to (1,0) ---")
    print(eng.render_ascii())

    # Player "interacts" with a new object (2,0)
    eng.interact((2, 0))
    eng.tick()
    print("--- after interact with (2,0) ---")
    print(eng.render_ascii())

    # Demonstrate δ-lift (layering)
    eng.lift((2, 0))
    for _ in range(2):
        eng.tick()
    print("--- after lifting (2,0) to higher layer ---")
    print(eng.render_ascii())

if __name__ == "__main__":
    demo()
