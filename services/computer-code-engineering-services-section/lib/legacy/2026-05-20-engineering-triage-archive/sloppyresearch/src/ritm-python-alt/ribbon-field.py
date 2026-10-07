#!/usr/bin/env python3
"""
ritopos_primary_ribbon_field.py
Render the complete Relational ∞-Topos as a ribbon field:
- background: all id→id relations (thin, translucent blue)
- overlay: primary :node-relations: (thick, red, curved, stronger "gravity")
"""

import re, sys, numpy as np, matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import FancyArrowPatch

# --- utility ---------------------------------------------------------------
def log(msg): print(f"\033[1;34m{msg}\033[0m")

def parse_edges(text):
    """Return all (src_id, tgt_id) pairs found anywhere."""
    pairs = re.findall(r"id:([0-9a-f-]{6,}).*?id:([0-9a-f-]{6,})", text, flags=re.I)
    return [(a,b) for a,b in pairs if a!=b]

def parse_primary_relations(text):
    """Return :node-relations: pairs as (src_id, src_lbl, tgt_id, tgt_lbl)."""
    pattern = r"\(\[\[id:([0-9a-f-]+)\]\]\[([^\]]+)\]\]\s*\.\s*\[\[id:([0-9a-f-]+)\]\]\[([^\]]+)\]\]\)"
    return re.findall(pattern, text, flags=re.I)

def layout_positions(edges):
    G = nx.DiGraph(); G.add_edges_from(edges)
    pos = nx.spring_layout(G, seed=42, k=0.7)   # stronger gravity
    return {n: np.array(p) for n,p in pos.items()}

# --- drawing ---------------------------------------------------------------
def draw_full_ribbon_field(text):
    log("Extracting edges and positions...")
    edges = parse_edges(text)
    coords = layout_positions(edges)

    primaries = parse_primary_relations(text)
    prim_ids = {(s,t) for (s,_,t,_) in primaries}

    fig, ax = plt.subplots(figsize=(10,10))
    ax.set_axis_off()
    log(f"Drawing {len(edges)} background relations and {len(primaries)} primary ribbons...")

    # Background blue ribbons
    for (src, tgt) in edges:
        if src not in coords or tgt not in coords: continue
        p0, p1 = coords[src], coords[tgt]
        mid = (p0 + p1)/2 + np.random.normal(scale=0.03, size=2)
        curve = np.random.uniform(-0.15,0.15)
        patch = FancyArrowPatch(p0, p1,
                                connectionstyle=f"arc3,rad={curve}",
                                arrowstyle='-',
                                lw=0.3, color='royalblue', alpha=0.04)
        ax.add_patch(patch)

    # Primary red ribbons (heavier gravity, thicker)
    for (src_id, src_lbl, tgt_id, tgt_lbl) in primaries:
        if src_id not in coords or tgt_id not in coords: continue
        p0, p1 = coords[src_id], coords[tgt_id]
        mid = (p0 + p1)/2 + np.random.normal(scale=0.1, size=2)
        curve = np.random.uniform(-0.25,0.25)
        patch = FancyArrowPatch(p0, p1,
                                connectionstyle=f"arc3,rad={curve}",
                                arrowstyle='-|>',
                                lw=2.2, color='crimson', alpha=0.8)
        ax.add_patch(patch)
        mid = (p0 + p1)/2
        ax.text(mid[0], mid[1], src_lbl, color='crimson',
                fontsize=7, ha='center', va='center', alpha=0.9)

    plt.title("RITopos Ribbon Field\nblue = background morphic flow • red = primary modal acts", fontsize=11)
    plt.tight_layout()
    plt.show()

# --- main ------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv)<2:
        print("usage: python3 ritopos_primary_ribbon_field.py /path/to/archive.txt")
        sys.exit(1)
    path = sys.argv[1]
    log(f"Reading archive from {path}")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    draw_full_ribbon_field(text)
