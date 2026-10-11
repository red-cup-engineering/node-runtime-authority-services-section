"""
analysis.py — Informational and geometric diagnostics for Relational ∞-Topos Cells

Analyzes output from:
    - cell.py          (constructive presheaf cells)
    - geometry.py      (cohesive geometric reflections)
    - physics.py       (field dynamics)

Provides:
    - Entropy metrics (Shannon, normalized)
    - Degree statistics (in/out/total)
    - Euler characteristic χ = |V| - |E|
    - Component counts (connected subgraphs)
    - Relational curvature (degree imbalance)
    - Curvature statistics (mean, variance)
    - Coherence index (bounded stability heuristic)

All functions are pure and finite.  Safe to run on any RelationalCell or GeometricCell.
"""

from __future__ import annotations
from typing import Dict, Set, Tuple, Union
import math
from statistics import mean, pstdev
from cell import RelationalCell
from geometry import GeometricCell

Node = Tuple[int, int]
YAdj = Dict[Node, Set[Node]]
RRel = Dict[Node, Set[Node]]

# -----------------------------------------------------------------------------
# --- Core utilities ----------------------------------------------------------
# -----------------------------------------------------------------------------

def nodes_edges_from(obj: Union[RelationalCell, GeometricCell]) -> Tuple[Set[Node], Set[Tuple[Node, Node]]]:
    """Extract node and edge sets uniformly from either cell type."""
    if isinstance(obj, RelationalCell):
        nodes = {n for src, dsts in obj.Y.items() for n in [src, *dsts]}
        edges = {(i,j) for i,js in obj.Y.items() for j in js}
    elif isinstance(obj, GeometricCell):
        nodes = set(obj.points.keys())
        edges = set(obj.edges)
    else:
        raise TypeError("Unsupported cell type")
    return nodes, edges

# -----------------------------------------------------------------------------
# --- Entropy -----------------------------------------------------------------
# -----------------------------------------------------------------------------

def shannon_entropy(obj: Union[RelationalCell, GeometricCell]) -> float:
    """
    Shannon entropy of edge-degree distribution:
        H = -∑_i p_i log₂ p_i,  where p_i = deg(i)/∑_j deg(j)
    """
    nodes, edges = nodes_edges_from(obj)
    if not nodes or not edges:
        return 0.0
    degrees = {n: 0 for n in nodes}
    for i, j in edges:
        degrees[i] = degrees.get(i, 0) + 1
    total = sum(degrees.values())
    if total == 0:
        return 0.0
    p = [deg / total for deg in degrees.values() if deg > 0]
    return -sum(pi * math.log2(pi) for pi in p)

def normalized_entropy(obj: Union[RelationalCell, GeometricCell]) -> float:
    """H / H_max = H / log₂(N)"""
    H = shannon_entropy(obj)
    N = len(nodes_edges_from(obj)[0])
    if N <= 1:
        return 0.0
    return H / math.log2(N)

# -----------------------------------------------------------------------------
# --- Topology ----------------------------------------------------------------
# -----------------------------------------------------------------------------

def euler_characteristic(obj: Union[RelationalCell, GeometricCell]) -> int:
    """χ = |V| - |E|"""
    nodes, edges = nodes_edges_from(obj)
    return len(nodes) - len(edges)

def connected_components(obj: Union[RelationalCell, GeometricCell]) -> int:
    """Return number of connected components (undirected)."""
    nodes, edges = nodes_edges_from(obj)
    if not nodes:
        return 0
    adj: Dict[Node, Set[Node]] = {n: set() for n in nodes}
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    seen = set()
    comps = 0
    for n in nodes:
        if n in seen:
            continue
        stack = [n]
        while stack:
            x = stack.pop()
            if x in seen: 
                continue
            seen.add(x)
            stack.extend(adj[x])
        comps += 1
    return comps

# -----------------------------------------------------------------------------
# --- Degree & Curvature ------------------------------------------------------
# -----------------------------------------------------------------------------

def degree_statistics(obj: Union[RelationalCell, GeometricCell]) -> Dict[str, float]:
    """Compute mean, stdev, and range of node degrees."""
    nodes, edges = nodes_edges_from(obj)
    deg = {n: 0 for n in nodes}
    for i, j in edges:
        deg[i] += 1
    vals = list(deg.values()) or [0]
    return {
        "mean": mean(vals),
        "stdev": pstdev(vals),
        "min": min(vals),
        "max": max(vals),
    }

def relational_curvature(obj: Union[RelationalCell, GeometricCell]) -> Dict[Node, float]:
    """
    Simple curvature measure: κ(n) = (in_deg - out_deg) / total_deg
    (for GeometricCell edges treated as directed).
    """
    nodes, edges = nodes_edges_from(obj)
    in_deg = {n: 0 for n in nodes}
    out_deg = {n: 0 for n in nodes}
    for i, j in edges:
        out_deg[i] += 1
        in_deg[j] += 1
    curv = {}
    for n in nodes:
        tot = in_deg[n] + out_deg[n]
        curv[n] = (in_deg[n] - out_deg[n]) / tot if tot > 0 else 0.0
    return curv

def curvature_stats(obj: Union[RelationalCell, GeometricCell]) -> Dict[str, float]:
    """Return mean and variance of curvature."""
    curv = list(relational_curvature(obj).values())
    if not curv:
        return {"mean": 0.0, "stdev": 0.0}
    return {"mean": mean(curv), "stdev": pstdev(curv)}

# -----------------------------------------------------------------------------
# --- Coherence ---------------------------------------------------------------
# -----------------------------------------------------------------------------

def coherence_index(obj: Union[RelationalCell, GeometricCell]) -> float:
    """
    Coherence index = normalized_entropy * (1 - |mean_curvature|).
    Heuristic for relational balance: high entropy but balanced flow.
    """
    Hn = normalized_entropy(obj)
    curv = curvature_stats(obj)
    return Hn * (1.0 - abs(curv["mean"]))

# -----------------------------------------------------------------------------
# --- Summary -----------------------------------------------------------------
# -----------------------------------------------------------------------------

def summary(obj: Union[RelationalCell, GeometricCell]) -> str:
    """Return formatted diagnostic summary."""
    H = shannon_entropy(obj)
    Hn = normalized_entropy(obj)
    χ = euler_characteristic(obj)
    comps = connected_components(obj)
    degs = degree_statistics(obj)
    curv = curvature_stats(obj)
    coh = coherence_index(obj)
    return (
        f"Entropy H = {H:.3f}  (norm {Hn:.3f})\n"
        f"Euler χ = {χ},  Components = {comps}\n"
        f"Degree: mean {degs['mean']:.2f}  ±{degs['stdev']:.2f}, "
        f"range [{degs['min']},{degs['max']}]\n"
        f"Curvature: mean {curv['mean']:.3f}  ±{curv['stdev']:.3f}\n"
        f"Coherence index = {coh:.3f}"
    )

# -----------------------------------------------------------------------------
# --- Demo --------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    from category import seed_object
    from geometry import from_relational_object
    X = seed_object(0, 1)
    G = from_relational_object(X)

    print("Diagnostic summary for base geometric cell:\n")
    print(summary(G))
