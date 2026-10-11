"""
physics.py — Field dynamics over cohesive geometric cells

Builds on:
    geometry.py  (Π, □geo, ◇geo, ∇, δgeo and GeometricCell/Point)

Capabilities:
- Node-wise scalar/vector fields on a GeometricCell
- Discrete differential operators: grad, div, Laplacian
- Simple time-steppers (Euler, semi-implicit / symplectic-ish)
- Energy functionals (kinetic, potential) + quick invariant checks
- Pullback/pushforward of fields along cohesive functors

Design notes:
- Keeps everything finite and terminating; no infinite δ lifting loops.
- Uses immutable Point replacement to avoid in-place geometry skew.

Author: em senn
Date: 2025-10-17
"""

from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Dict, Tuple, Callable, Optional, Iterable
import math

from geometry import (
    GeometricCell, Point,
    PI, BOX_GEO, DIAMOND_GEO, NABLA, DELTA_GEO,
    from_relational_object, visualize_ascii
)
from category import seed_object

Node = Tuple[int, int]
Scalar = float
Vec2 = Tuple[float, float]


# -----------------------------------------------------------------------------
# Field containers
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ScalarField:
    """Node-wise scalar field φ : nodes → ℝ."""
    data: Dict[Node, Scalar]

    def pullback(self, F: Callable[[GeometricCell], GeometricCell],
                 src: GeometricCell) -> "ScalarField":
        """
        Pull φ back along F: F*φ defined on nodes of F(src) by nearest-node copy.
        (Minimal, discrete approximation.)
        """
        tgt = F(src)
        out = {}
        for n, p in tgt.points.items():
            # choose nearest original node in src (Euclidean)
            cn = min(src.points.items(),
                     key=lambda kv: (kv[1].x - p.x)**2 + (kv[1].y - p.y)**2)[0]
            out[n] = self.data.get(cn, 0.0)
        return ScalarField(out)


@dataclass(frozen=True)
class VectorField:
    """Node-wise vector field v : nodes → ℝ^2."""
    data: Dict[Node, Vec2]

    def pullback(self, F: Callable[[GeometricCell], GeometricCell],
                 src: GeometricCell) -> "VectorField":
        """
        Pull v back along F (nearest-node copy, keeping the vector).
        """
        tgt = F(src)
        out = {}
        for n, p in tgt.points.items():
            cn = min(src.points.items(),
                     key=lambda kv: (kv[1].x - p.x)**2 + (kv[1].y - p.y)**2)[0]
            out[n] = self.data.get(cn, (0.0, 0.0))
        return VectorField(out)


# -----------------------------------------------------------------------------
# Discrete differential operators
# -----------------------------------------------------------------------------

def neighbors(cell: GeometricCell, n: Node) -> Iterable[Node]:
    for (i, j) in cell.edges:
        if i == n:
            yield j

def gradient(cell: GeometricCell, phi: ScalarField, eps: float = 1e-9) -> VectorField:
    """
    Discrete (outgoing) gradient: grad φ (n) ≈ avg over neighbors (φ(j)-φ(n)) * unit(n→j).
    """
    out: Dict[Node, Vec2] = {}
    for n, p in cell.points.items():
        accx = accy = 0.0
        cnt = 0
        for j in neighbors(cell, n):
            pj = cell.points.get(j)
            if pj is None:
                continue
            dx = pj.x - p.x
            dy = pj.y - p.y
            dist = math.hypot(dx, dy) + eps
            u = (dx / dist, dy / dist)
            accx += (phi.data.get(j, 0.0) - phi.data.get(n, 0.0)) * u[0]
            accy += (phi.data.get(j, 0.0) - phi.data.get(n, 0.0)) * u[1]
            cnt += 1
        if cnt > 0:
            out[n] = (accx / cnt, accy / cnt)
        else:
            out[n] = (0.0, 0.0)
    return VectorField(out)

def divergence(cell: GeometricCell, v: VectorField, eps: float = 1e-9) -> ScalarField:
    """
    Discrete divergence: div v (n) ≈ avg over neighbors ⟨v(j)-v(n), unit(n→j)⟩.
    """
    out: Dict[Node, float] = {}
    for n, p in cell.points.items():
        vn = v.data.get(n, (0.0, 0.0))
        acc = 0.0
        cnt = 0
        for j in neighbors(cell, n):
            pj = cell.points.get(j)
            if pj is None:
                continue
            dx = pj.x - p.x
            dy = pj.y - p.y
            dist = math.hypot(dx, dy) + eps
            u = (dx / dist, dy / dist)
            vj = v.data.get(j, (0.0, 0.0))
            acc += (vj[0] - vn[0]) * u[0] + (vj[1] - vn[1]) * u[1]
            cnt += 1
        out[n] = acc / cnt if cnt > 0 else 0.0
    return ScalarField(out)

def laplacian(cell: GeometricCell, phi: ScalarField) -> ScalarField:
    """
    Graph Laplacian: Δφ(n) ≈ avg_neighbors φ(j) - φ(n).
    """
    out: Dict[Node, float] = {}
    for n, _ in cell.points.items():
        cnt = 0
        s = 0.0
        for j in neighbors(cell, n):
            s += phi.data.get(j, 0.0)
            cnt += 1
        out[n] = (s / cnt - phi.data.get(n, 0.0)) if cnt > 0 else 0.0
    return ScalarField(out)


# -----------------------------------------------------------------------------
# Energies / potentials
# -----------------------------------------------------------------------------

def kinetic_energy(cell: GeometricCell, v: VectorField, mass: float = 1.0) -> float:
    return 0.5 * mass * sum(vx*vx + vy*vy for (vx, vy) in v.data.values())

def potential_energy(cell: GeometricCell, phi: ScalarField, k: float = 1.0) -> float:
    # Simple quadratic potential ∑ 0.5 k φ^2
    return 0.5 * k * sum(val*val for val in phi.data.values())

def total_energy(cell: GeometricCell, v: VectorField, phi: ScalarField,
                 mass: float = 1.0, k: float = 1.0) -> float:
    return kinetic_energy(cell, v, mass) + potential_energy(cell, phi, k)


# -----------------------------------------------------------------------------
# Time integrators
# -----------------------------------------------------------------------------

def euler_step_positions(cell: GeometricCell, v: VectorField, dt: float) -> GeometricCell:
    """
    x_{t+dt} = x_t + v * dt   (node-wise)
    """
    pts = {}
    for n, p in cell.points.items():
        vx, vy = v.data.get(n, (0.0, 0.0))
        pts[n] = Point(p.x + vx * dt, p.y + vy * dt, p.level)
    return GeometricCell(points=pts, edges=set(cell.edges), relations=set(cell.relations))

def euler_step_field(phi: ScalarField, rhs: ScalarField, dt: float) -> ScalarField:
    """
    φ_{t+dt} = φ_t + rhs * dt
    """
    out = {n: phi.data.get(n, 0.0) + rhs.data.get(n, 0.0) * dt
           for n in set(phi.data.keys()) | set(rhs.data.keys())}
    return ScalarField(out)

def semi_implicit_step(
    cell: GeometricCell,
    v: VectorField,
    phi: ScalarField,
    grad_potential: Callable[[GeometricCell, ScalarField], VectorField],
    dt: float,
    mass: float = 1.0
) -> Tuple[GeometricCell, VectorField]:
    """
    Symplectic-ish update:
        v_{t+dt} = v_t - (dt/m) * ∇U(φ_t)
        x_{t+dt} = x_t + dt * v_{t+dt}
    """
    force = grad_potential(cell, phi)  # returns vector field “∇U”
    # velocity update
    new_v = {}
    for n, vec in v.data.items():
        fx, fy = force.data.get(n, (0.0, 0.0))
        new_v[n] = (vec[0] - (dt / mass) * fx, vec[1] - (dt / mass) * fy)
    v2 = VectorField(new_v)
    # position update
    cell2 = euler_step_positions(cell, v2, dt)
    return cell2, v2


# -----------------------------------------------------------------------------
# A sample potential: link-spring energy on edges
# -----------------------------------------------------------------------------

def spring_potential_gradient(cell: GeometricCell, phi: ScalarField,
                              k: float = 1.0, rest: float = 1.0) -> VectorField:
    """
    Interpret φ(n) as a per-node “rest length scale.”
    The potential penalizes stretched/shrunk edges; gradient gives forces.
    """
    forces: Dict[Node, Vec2] = {n: (0.0, 0.0) for n in cell.points}
    for (i, j) in cell.edges:
        pi = cell.points[i]; pj = cell.points[j]
        dx, dy = pj.x - pi.x, pj.y - pi.y
        L = math.hypot(dx, dy) + 1e-9
        u = (dx / L, dy / L)
        # target length uses average of φ(i), φ(j)
        L0 = rest * (0.5 * (phi.data.get(i, 1.0) + phi.data.get(j, 1.0)))
        fmag = k * (L - L0)
        fi = ( fmag * u[0],  fmag * u[1])
        fj = (-fmag * u[0], -fmag * u[1])
        # accumulate
        f_ix, f_iy = forces[i]
        f_jx, f_jy = forces[j]
        forces[i] = (f_ix + fi[0], f_iy + fi[1])
        forces[j] = (f_jx + fj[0], f_jy + fj[1])
    return VectorField(forces)


# -----------------------------------------------------------------------------
# Cohesive functor interaction (push/pull)
# -----------------------------------------------------------------------------

def pullback_scalar(F, cell: GeometricCell, phi: ScalarField) -> Tuple[GeometricCell, ScalarField]:
    tgt = F.map_obj(cell)
    return tgt, phi.pullback(lambda X: F.map_obj(X), cell)

def pullback_vector(F, cell: GeometricCell, v: VectorField) -> Tuple[GeometricCell, VectorField]:
    tgt = F.map_obj(cell)
    return tgt, v.pullback(lambda X: F.map_obj(X), cell)


# -----------------------------------------------------------------------------
# Demo / smoke test
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Seed a tiny relational object and lift to geometry
    X = seed_object(0, 1)
    G = from_relational_object(X)

    # Define simple initial fields
    phi0 = ScalarField({n: 1.0 for n in G.points})          # uniform scalar “size”
    v0   = VectorField({n: (0.1, 0.0) for n in G.points})    # small rightward flow

    print("Base geometric chart:")
    print(visualize_ascii(G))

    # Energy before
    E0 = total_energy(G, v0, phi0)
    print(f"Initial total energy: {E0:.6f}")

    # One cohesive transform (flat path-space) + pull back fields
    Gf, phi_f = pullback_scalar(BOX_GEO, G, phi0)
    _,   v_f  = pullback_vector(BOX_GEO, G, v0)

    # Step dynamics a few iterations (bounded)
    Gt, vt = Gf, v_f
    for step in range(10):
        Gt, vt = semi_implicit_step(
            Gt, vt, phi_f,
            grad_potential=lambda cell, phi: spring_potential_gradient(cell, phi, k=0.5, rest=1.0),
            dt=0.1, mass=1.0
        )

    Ef = total_energy(Gt, vt, phi_f)
    print(f"Final total energy (after 10 steps): {Ef:.6f}")
    print("Final chart (ascii):")
    print(visualize_ascii(Gt))
