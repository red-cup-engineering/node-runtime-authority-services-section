#!/usr/bin/env python3
import sys, re, numpy as np, matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import FancyArrowPatch
from matplotlib.collections import PatchCollection

def parse_edges(text):
    pairs = re.findall(r"id:([0-9a-f-]{6,}).*?id:([0-9a-f-]{6,})", text, flags=re.I)
    return [(a,b) for a,b in pairs if a!=b]

def layout_positions(edges):
    G = nx.DiGraph(); G.add_edges_from(edges)
    pos = nx.spring_layout(G, seed=42, k=0.5)
    return {n: np.array(p) for n,p in pos.items()}

def draw_ribbon_field(edges, coords):
    plt.figure(figsize=(10,10))
    patches = []
    for (src, tgt) in edges:
        if src not in coords or tgt not in coords: continue
        p0, p1 = coords[src], coords[tgt]
        # mid control point for gentle curve
        mid = (p0 + p1)/2 + np.random.normal(scale=0.02, size=2)
        path = np.array([p0, mid, p1])
        # draw as a translucent curved arrow
        patch = FancyArrowPatch(path[0], path[2],
                                connectionstyle=f"arc3,rad={np.random.uniform(-0.3,0.3)}",
                                arrowstyle='-|>', lw=0.4,
                                color='royalblue', alpha=0.05)
        plt.gca().add_patch(patch)
    plt.axis("off")
    plt.title("RITopos ribbon field — continuous morphic flow", fontsize=12)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    if len(sys.argv)<2:
        print("usage: python3 ritopos_ribbons.py /path/to/archive.txt"); sys.exit(1)
    text = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
    edges = parse_edges(text)
    coords = layout_positions(edges)
    draw_ribbon_field(edges, coords)
