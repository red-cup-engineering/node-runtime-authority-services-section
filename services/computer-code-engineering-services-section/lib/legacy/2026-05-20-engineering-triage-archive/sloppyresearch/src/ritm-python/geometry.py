"""
geometry.py — Cohesive geometric reflection of the Relational ∞-Topos Cell

This layer lifts categorical RITM structure into a *geometric* one,
interpreting relational cells as local charts of smooth cohesive spaces.

Each RelationalObject becomes a *geometric chart* G(X):
    - nodes -> points in a local manifold patch
    - Y edges -> differentiable structure (flows)
    - R relations -> metric / connection constraints

Functorial structure:
    Π→   : geometric 'shape' functor (integration along path)
    □    : 'flat' space of paths  (Map(I_d, X))
    ◇    : 'sharp' dual path space (Map(X, I_d))
    ∇←   : 'codiscrete' / global section functor (limit)
    δgeo : local lift of fibres (connection / differential)

All are endofunctors on the category of GeometricCells.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Set, Tuple, List
import math

from category import (
    RelationalObject,
    Functor,
    BOX, DIAMOND, COMPOSITE, DELTA
)

# ---------------------------------------------------------------------
# --- Geometric primitives --------------------------------------------
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class Point:
    """A smooth-space point with coordinates (x,y,level)."""
    x: float
    y: float
    level: int = 0

@dataclass
class GeometricCell:
    """
    Geometric realization of a relational object.
    Points correspond to nodes; edges become local vector fields.
    """
    points: Dict[Tuple[int, int], Point]
    edges: Set[Tuple[Tuple[int,int], Tuple[int,int]]]
    relations: Set[Tuple[Tuple[int,int], Tuple[int,int]]]

    def as_relational_object(self) -> RelationalObject:
        """Forget geometry -> return underlying combinatorial cell."""
        Y = {}
        for (i,j) in self.edges:
            Y.setdefault(i, set()).add(j)
        R = {}
        for (i,j) in self.relations:
            R.setdefault(i, set()).add(j)
            R.setdefault(j, set()).add(i)
        return RelationalObject(Y=Y, R=R)

# ---------------------------------------------------------------------
# --- Smooth-space transforms -----------------------------------------
# ---------------------------------------------------------------------

def shape(cell: GeometricCell) -> GeometricCell:
    """
    Π→ : Shape functor — collapse paths to endpoints (integration along I_d).
    In discrete terms: retain points but remove internal edges.
    """
    pts = dict(cell.points)
    # Remove interior edges (those forming 2-step chains)
    new_edges = set()
    for (i,j) in cell.edges:
        if all(k not in cell.edges for k in [(i,j)]):
            new_edges.add((i,j))
    return GeometricCell(points=pts, edges=new_edges, relations=set(cell.relations))

def flat(cell: GeometricCell) -> GeometricCell:
    """
    □ : Flat functor — space of paths (Map(I_d, X)).
    Duplicate points along a synthetic time axis to simulate tangent bundle.
    """
    pts = {}
    for (nid, lvl), p in cell.points.items():
        pts[(nid, lvl)] = Point(p.x, p.y, p.level)
        pts[(nid, lvl+1)] = Point(p.x + 0.0, p.y + 0.0, p.level + 1)
    edges = set(cell.edges)
    # Add vertical lifts
    for (nid, lvl) in list(pts.keys()):
        lifted = (nid, lvl+1)
        if lifted in pts:
            edges.add(((nid,lvl), lifted))
    return GeometricCell(points=pts, edges=edges, relations=set(cell.relations))

def sharp(cell: GeometricCell) -> GeometricCell:
    """
    ◇ : Sharp functor — dual path space (Map(X, I_d)).
    Transpose edges (reverse orientation).
    """
    pts = dict(cell.points)
    edges = {(j,i) for (i,j) in cell.edges}
    return GeometricCell(points=pts, edges=edges, relations=set(cell.relations))

def codiscrete(cell: GeometricCell) -> GeometricCell:
    """
    ∇← : Codiscrete functor — global section / limit.
    Every point connected to every other (discrete global binding).
    """
    pts = dict(cell.points)
    all_pairs = {(i,j) for i in pts for j in pts if i != j}
    return GeometricCell(points=pts, edges=all_pairs, relations=all_pairs)

def delta_geo(cell: GeometricCell) -> GeometricCell:
    """
    δ_geo : Geometric fibre lift (connection).
    Adds small offset points in tangent direction to simulate differentiation.
    """
    pts = dict(cell.points)
    new_pts = {}
    for (nid, lvl), p in pts.items():
        lifted = (nid, lvl+1)
        new_pts[lifted] = Point(p.x + 0.1, p.y + 0.1, p.level + 1)
    pts.update(new_pts)
    edges = set(cell.edges)
    edges |= {((nid, lvl), (nid, lvl+1)) for (nid, lvl) in pts}
    return GeometricCell(points=pts, edges=edges, relations=set(cell.relations))

# ---------------------------------------------------------------------
# --- Cohesive functors ------------------------------------------------
# ---------------------------------------------------------------------

PI = Functor(on_obj=lambda X: shape(X), on_mor=lambda f: f, name="Π")
BOX_GEO = Functor(on_obj=lambda X: flat(X), on_mor=lambda f: f, name="□geo")
DIAMOND_GEO = Functor(on_obj=lambda X: sharp(X), on_mor=lambda f: f, name="◇geo")
NABLA = Functor(on_obj=lambda X: codiscrete(X), on_mor=lambda f: f, name="∇")
DELTA_GEO = Functor(on_obj=lambda X: delta_geo(X), on_mor=lambda f: f, name="δgeo")

# ---------------------------------------------------------------------
# --- Conversion utilities --------------------------------------------
# ---------------------------------------------------------------------

def from_relational_object(X: RelationalObject) -> GeometricCell:
    """Embed a RelationalObject as a geometric chart with planar coordinates."""
    pts = {}
    for (nid,lvl) in X.Y.keys():
        pts[(nid,lvl)] = Point(float(nid), float(lvl))
    for js in X.Y.values():
        for (nid,lvl) in js:
            if (nid,lvl) not in pts:
                pts[(nid,lvl)] = Point(float(nid), float(lvl))
    edges = {(i,j) for i,js in X.Y.items() for j in js}
    relations = {(i,j) for i,js in X.R.items() for j in js}
    return GeometricCell(points=pts, edges=edges, relations=relations)

def visualize_ascii(cell: GeometricCell) -> str:
    """
    Very minimal ASCII layout: prints node levels and connectivity.
    """
    lines = []
    for (nid,lvl), p in sorted(cell.points.items()):
        targets = [str(j) for (i,j) in cell.edges if i==(nid,lvl)]
        lines.append(f"{(nid,lvl)} -> {targets}")
    return "\n".join(lines)


# ---------------------------------------------------------------------
# --- Demonstration ---------------------------------------------------
# ---------------------------------------------------------------------

if __name__ == "__main__":
    from category import seed_object
    X = seed_object(0,1)
    G = from_relational_object(X)

    print("Base geometric chart:")
    print(visualize_ascii(G))

    for F in [PI, BOX_GEO, DIAMOND_GEO, NABLA, DELTA_GEO]:
        Gp = F.map_obj(G)
        print(f"\n{F.name}(G):")
        print(visualize_ascii(Gp))
