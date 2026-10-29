#!/usr/bin/env python3
"""
ritopos_field.py — visualize a Relational ∞-Topos as a pure arrow field.
No points, no graph structure — only directed morphic flow.

Usage:
    python3 ritopos_field.py /path/to/archive.txt
"""

import sys, re, numpy as np, matplotlib.pyplot as plt
import networkx as nx

def log(msg): print(f"\033[1;34m{msg}\033[0m")

# ------------------------------------------------------------
# Parse all id→id pairs
# ------------------------------------------------------------
def parse_edges(text):
    pairs = re.findall(r"id:([0-9a-f-]{6,}).*?id:([0-9a-f-]{6,})", text, flags=re.I)
    edges = [(a,b) for a,b in pairs if a!=b]
    log(f"Extracted {len(edges)} arrow relations.")
    return edges

# ------------------------------------------------------------
# Layout positions (for flow directions)
# ------------------------------------------------------------
def layout_positions(edges):
    G = nx.DiGraph()
    G.add_edges_from(edges)
    pos = nx.spring_layout(G, seed=42, k=0.5)  # 2D coordinates for ids
    coords = {n: np.array(p) for n,p in pos.items()}
    return coords

# ------------------------------------------------------------
# Draw the arrow field
# ------------------------------------------------------------
def draw_arrow_field(edges, coords):
    plt.figure(figsize=(9,9))
    xs, ys, dxs, dys = [], [], [], []
    for (src, tgt) in edges:
        if src in coords and tgt in coords:
            x0,y0 = coords[src]
            x1,y1 = coords[tgt]
            dx, dy = x1-x0, y1-y0
            norm = np.hypot(dx,dy)
            if norm == 0: continue
            dxs.append(dx/norm)
            dys.append(dy/norm)
            xs.append(x0)
            ys.append(y0)
    xs, ys, dxs, dys = map(np.array, (xs, ys, dxs, dys))

    log(f"Rendering {len(xs)} arrows as morphic flow field...")
    plt.quiver(xs, ys, dxs, dys,
               angles='xy', scale_units='xy', scale=20,
               width=0.002, color='royalblue', alpha=0.35)
    plt.axis("off")
    plt.title("Arrow-only RITopos — morphic flow of relations", fontsize=12)
    plt.tight_layout()
    plt.show()

# ------------------------------------------------------------
# __main__
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 ritopos_field.py /path/to/archive.txt")
        sys.exit(1)

    path = sys.argv[1]
    log(f"Reading archive from {path}")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    edges = parse_edges(text)
    if not edges:
        log("No arrow relations found — check your archive format.")
        sys.exit(0)

    coords = layout_positions(edges)
    draw_arrow_field(edges, coords)
