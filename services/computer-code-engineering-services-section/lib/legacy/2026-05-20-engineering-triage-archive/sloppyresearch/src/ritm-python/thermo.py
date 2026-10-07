"""
thermo.py — atomic thermo/continuum primitives over your GeometricCell + Field types.

Designed to compose with physics.py:
  - ScalarField, VectorField
  - gradient, divergence, laplacian
  - euler_step_field, euler_step_positions, etc.

All functions are pure (return new fields/cells) and avoid new abstractions.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, Iterable, Callable
import math

from geometry import GeometricCell, Point
from physics import (
    ScalarField, VectorField,
    gradient, divergence, laplacian,
    euler_step_field
)

Node = Tuple[int, int]
Vec2 = Tuple[float, float]

# -----------------------------------------------------------------------------
# Field algebra (tiny, composable helpers)
# -----------------------------------------------------------------------------

def s_add(a: ScalarField, b: ScalarField, w: float = 1.0) -> ScalarField:
    keys = set(a.data) | set(b.data)
    return ScalarField({n: a.data.get(n, 0.0) + w * b.data.get(n, 0.0) for n in keys})

def s_mul(a: ScalarField, k: float) -> ScalarField:
    return ScalarField({n: k * v for n, v in a.data.items()})

def v_add(a: VectorField, b: VectorField, w: float = 1.0) -> VectorField:
    keys = set(a.data) | set(b.data)
    out: Dict[Node, Vec2] = {}
    for n in keys:
        ax, ay = a.data.get(n, (0.0, 0.0))
        bx, by = b.data.get(n, (0.0, 0.0))
        out[n] = (ax + w * bx, ay + w * by)
    return VectorField(out)

def v_mul(a: VectorField, k: float) -> VectorField:
    return VectorField({n: (k*vx, k*vy) for n, (vx, vy) in a.data.items()})

def v_norm(a: VectorField) -> ScalarField:
    return ScalarField({n: math.hypot(vx, vy) for n, (vx, vy) in a.data.items()})

# -----------------------------------------------------------------------------
# Semi-Lagrangian advection (stable transport)
# -----------------------------------------------------------------------------

def _backtrace(cell: GeometricCell, n: Node, v: VectorField, dt: float) -> Node:
    """
    Nearest-node backtrace: x* = x_n - v(n)*dt, snap to nearest existing node.
    Discrete & cheap; good enough for graph-like charts.
    """
    p = cell.points[n]
    vx, vy = v.data.get(n, (0.0, 0.0))
    xq, yq = p.x - vx*dt, p.y - vy*dt
    # nearest neighbor on the same chart
    best = n
    bestd = float("inf")
    for m, q in cell.points.items():
        d = (q.x - xq)**2 + (q.y - yq)**2
        if d < bestd:
            bestd = d
            best = m
    return best

def advect_scalar(cell: GeometricCell, phi: ScalarField, v: VectorField, dt: float) -> ScalarField:
    out = {}
    for n in cell.points:
        src = _backtrace(cell, n, v, dt)
        out[n] = phi.data.get(src, 0.0)
    return ScalarField(out)

def advect_vector(cell: GeometricCell, u: VectorField, v: VectorField, dt: float) -> VectorField:
    out = {}
    for n in cell.points:
        src = _backtrace(cell, n, v, dt)
        out[n] = u.data.get(src, (0.0, 0.0))
    return VectorField(out)

# -----------------------------------------------------------------------------
# Diffusion & Heat equation
# -----------------------------------------------------------------------------

def diffuse_scalar(cell: GeometricCell, phi: ScalarField, kappa: float, dt: float) -> ScalarField:
    """
    Explicit Euler diffusion: φ' = φ + dt * κ * Δφ
    Stable if dt <= O(h^2/κ); on irregular charts keep dt small.
    """
    lap = laplacian(cell, phi)
    return euler_step_field(phi, s_mul(lap, kappa), dt)

def heat_step(cell: GeometricCell,
              T: ScalarField,
              v: VectorField,
              dt: float,
              kappa: float,
              source: ScalarField | None = None) -> ScalarField:
    """
    Advection-diffusion-source update for temperature-like scalar.
      1) advect
      2) diffuse
      3) add source
    """
    adv = advect_scalar(cell, T, v, dt)
    dif = diffuse_scalar(cell, adv, kappa, dt)
    return s_add(dif, source, w=dt) if source else dif

# -----------------------------------------------------------------------------
# Thermodynamic relations as FIELD morphisms (idealized)
# -----------------------------------------------------------------------------

def ideal_gas_pressure(rho: ScalarField, T: ScalarField, R_specific: float = 287.0) -> ScalarField:
    """
    p = ρ R T  (scalar fields must be defined on the same node set)
    """
    keys = set(rho.data) | set(T.data)
    return ScalarField({n: rho.data.get(n, 0.0) * R_specific * T.data.get(n, 0.0) for n in keys})

def clausius_clapeyron(T: ScalarField,
                       L: float = 2.5e6,    # J/kg
                       Rv: float = 461.5,   # J/kg/K
                       T0: float = 273.15,
                       e0: float = 611.2) -> ScalarField:
    """
    Saturation vapor pressure field e_s(T) via Clausius–Clapeyron.
    """
    out = {}
    for n, Tk in T.data.items():
        out[n] = e0 * math.exp(L/Rv * (1.0/T0 - 1.0/max(150.0, Tk)))
    return ScalarField(out)

def potential_temperature(T: ScalarField, p: ScalarField, p0: float = 1.0e5, kappa: float = 0.2854) -> ScalarField:
    """
    θ = T (p0/p)^κ  (dry-air)
    """
    keys = set(T.data) | set(p.data)
    out = {}
    for n in keys:
        t = T.data.get(n, 0.0)
        pp = max(1.0, p.data.get(n, p0))
        out[n] = t * (p0/pp) ** kappa
    return ScalarField(out)

# -----------------------------------------------------------------------------
# Incompressible projection (pressure-Poisson solve + velocity correction)
# -----------------------------------------------------------------------------

def jacobi_poisson(cell: GeometricCell,
                   rhs: ScalarField,
                   iters: int = 40,
                   alpha: float = 1.0) -> ScalarField:
    """
    Very simple Poisson solver for ∇²p = rhs using Jacobi iterations on the graph Laplacian.
    alpha can be tuned if your Laplacian scaling differs.
    """
    p = ScalarField({n: 0.0 for n in cell.points})
    for _ in range(iters):
        lap_p = laplacian(cell, p)
        # p <- p + alpha*(rhs - lap_p)
        corr = s_add(rhs, s_mul(lap_p, -1.0))
        p = s_add(p, s_mul(corr, alpha))
    return p

def project_incompressible(cell: GeometricCell,
                           u: VectorField,
                           iters: int = 40,
                           alpha: float = 1.0) -> tuple[VectorField, ScalarField]:
    """
    Hodge-like projection on graph:
      1) compute divergence d = ∇·u
      2) solve ∇²p = d
      3) set u' = u - ∇p
    Returns corrected velocity and pressure field.
    """
    d = divergence(cell, u)
    p = jacobi_poisson(cell, d, iters=iters, alpha=alpha)
    gp = gradient(cell, p)
    u_corr = v_add(u, v_mul(gp, -1.0))
    return u_corr, p

# -----------------------------------------------------------------------------
# Diagnostics
# -----------------------------------------------------------------------------

def total_mass(phi: ScalarField) -> float:
    return sum(phi.data.values())

def total_heat(rho: ScalarField, c_p: float, T: ScalarField) -> float:
    keys = set(rho.data) | set(T.data)
    return sum(rho.data.get(n,0.0)*c_p*T.data.get(n,0.0) for n in keys)

def flux_through(cell: GeometricCell,
                 u: VectorField,
                 predicate: Callable[[Node], bool]) -> float:
    """
    Sum of outward flux across all edges whose source satisfies predicate.
    ⟨u(j)-u(i), unit(i→j)⟩, averaged like divergence but only over a cut.
    """
    acc = 0.0
    for (i, j) in cell.edges:
        if not predicate(i): 
            continue
        pi, pj = cell.points[i], cell.points[j]
        dx, dy = pj.x - pi.x, pj.y - pi.y
        L = math.hypot(dx, dy) + 1e-9
        ux, uy = u.data.get(j, (0.0, 0.0))
        vx, vy = u.data.get(i, (0.0, 0.0))
        acc += ((ux - vx) * dx + (uy - vy) * dy) / L
    return acc

def entropy_proxy(phi: ScalarField, eps: float = 1e-12) -> float:
    """
    Shannon-like entropy on a nonnegative scalar field normalized to sum=1.
    """
    vals = [max(0.0, v) for v in phi.data.values()]
    s = sum(vals) + eps
    return -sum((v/s) * math.log((v/s) + eps) for v in vals if v > 0.0)
