"""
rasterizer.py — Relational/Categorical raster graphics module

Purpose:
    Convert a relational / cohesive structure (Y,R) or GeometricCell
    into a 2D raster image — real graphics, not terminal text.

Dependencies:
    numpy, pillow (PIL)

    pip install numpy pillow

Design:
    1. Extract graph topology from (Y,R).
    2. Compute a 2D layout from connectivity (spectral or force-based).
    3. Evaluate a scalar field per node (heat, curvature, degree, etc.).
    4. Paint the result into a NumPy RGB array.
    5. Export to PNG or return array.

Use:
    from rasterizer import rasterize_relational, save_image

    img = rasterize_relational(cell.Y, cell.R, field=heat)
    save_image(img, "frame_001.png")
"""

import numpy as np
from PIL import Image
from math import sqrt
from typing import Dict, Tuple, Set, Optional

Node = Tuple[int, int]


# ---------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------

def normalize_coords(coords: Dict[Node, np.ndarray]) -> Dict[Node, np.ndarray]:
    """Rescale coordinates into [0,1]×[0,1]."""
    arr = np.array(list(coords.values()))
    if arr.size == 0:
        return coords
    mins = arr.min(axis=0)
    maxs = arr.max(axis=0)
    span = np.maximum(maxs - mins, 1e-9)
    out = {}
    for n, xy in coords.items():
        out[n] = (xy - mins) / span
    return out


def colormap(v: float) -> Tuple[int, int, int]:
    """Simple perceptual blue→yellow map."""
    v = np.clip(v, 0.0, 1.0)
    return (
        int(255 * v),
        int(255 * np.sqrt(v)),
        int(255 * (1.0 - v))
    )


# ---------------------------------------------------------------------
# Layouts
# ---------------------------------------------------------------------

def force_layout(Y: Dict[Node, Set[Node]], steps: int = 128, lr: float = 0.02) -> Dict[Node, np.ndarray]:
    """
    Simple force-directed layout (Fruchterman–Reingold style).
    Returns 2D coordinates in [0,1]^2.
    """
    nodes = sorted(set(Y.keys()) | {b for outs in Y.values() for b in outs})
    n = len(nodes)
    if n == 0:
        return {}

    idx = {node: i for i, node in enumerate(nodes)}
    pos = np.random.rand(n, 2)  # initial random positions
    area = 1.0
    k = sqrt(area / n)

    for _ in range(steps):
        disp = np.zeros_like(pos)
        # repulsive forces
        for i in range(n):
            delta = pos[i] - pos
            dist = np.linalg.norm(delta, axis=1) + 1e-6
            rep = (k ** 2 / dist ** 2)[:, None] * (delta / dist[:, None])
            disp[i] += rep.sum(axis=0)
        # attractive forces
        for a, outs in Y.items():
            for b in outs:
                if a not in idx or b not in idx:
                    continue
                i, j = idx[a], idx[b]
                delta = pos[i] - pos[j]
                dist = np.linalg.norm(delta) + 1e-6
                attr = (dist ** 2 / k) * (delta / dist)
                disp[i] -= attr
                disp[j] += attr
        # update
        pos += lr * disp
        # clamp to box
        pos = np.clip(pos, 0.0, 1.0)

    coords = {node: pos[i] for node, i in idx.items()}
    return normalize_coords(coords)


# ---------------------------------------------------------------------
# Rasterization
# ---------------------------------------------------------------------

def rasterize_relational(
    Y: Dict[Node, Set[Node]],
    R: Dict[Node, Set[Node]],
    field: Optional[Dict[Node, float]] = None,
    size: Tuple[int, int] = (512, 512),
    node_radius: int = 6,
    edge_alpha: float = 0.25,
    bg_color: Tuple[int, int, int] = (8, 8, 12),
) -> np.ndarray:
    """
    Produce a raster RGB image from the relational graph.

    Parameters
    ----------
    Y : dict
        Directed edges.
    R : dict
        Symmetric relations (ignored for layout, used for glow).
    field : dict
        Optional scalar field per node (0..1 range recommended).
    size : (w, h)
        Output resolution in pixels.
    node_radius : int
        Radius (in pixels) of node blobs.
    edge_alpha : float
        Opacity for drawing edges.
    """
    W, H = size
    coords = force_layout(Y)
    img = np.zeros((H, W, 3), dtype=np.float32)
    if not coords:
        return img

    # edges (faint)
    for a, outs in Y.items():
        if a not in coords:
            continue
        xa, ya = coords[a]
        for b in outs:
            if b not in coords:
                continue
            xb, yb = coords[b]
            x0, y0 = int(xa * W), int(ya * H)
            x1, y1 = int(xb * W), int(yb * H)
            num = int(np.hypot(x1 - x0, y1 - y0))
            if num == 0: 
                continue
            xs = np.linspace(x0, x1, num)
            ys = np.linspace(y0, y1, num)
            for xi, yi in zip(xs.astype(int), ys.astype(int)):
                if 0 <= xi < W and 0 <= yi < H:
                    img[yi, xi, :] += edge_alpha

    # nodes
    for n, (x, y) in coords.items():
        cx, cy = int(x * W), int(y * H)
        value = field.get(n, 0.5) if field else 0.5
        color = np.array(colormap(value), dtype=np.float32) / 255.0
        rr = node_radius
        for dy in range(-rr, rr + 1):
            for dx in range(-rr, rr + 1):
                xx, yy = cx + dx, cy + dy
                if 0 <= xx < W and 0 <= yy < H:
                    d2 = dx * dx + dy * dy
                    if d2 <= rr * rr:
                        falloff = 1.0 - sqrt(d2) / rr
                        img[yy, xx, :] += color * falloff

    # relations: draw glow for symmetric neighbors
    for a, peers in R.items():
        if a not in coords:
            continue
        xa, ya = coords[a]
        for b in peers:
            if b not in coords:
                continue
            xb, yb = coords[b]
            cx, cy = int((xa + xb) / 2 * W), int((ya + yb) / 2 * H)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    xx, yy = cx + dx, cy + dy
                    if 0 <= xx < W and 0 <= yy < H:
                        img[yy, xx, :] += (0.4, 0.6, 1.0)

    # tone map
    img = np.clip(img, 0.0, 1.0)
    img = (bg_color / np.array([255, 255, 255])) + (1 - bg_color[0]/255) * img
    img = np.clip(img * 255.0, 0, 255).astype(np.uint8)
    return img


# ---------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------

def save_image(img: np.ndarray, path: str):
    """Save RGB numpy array to a PNG file."""
    Image.fromarray(img).save(path)


# ---------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------

if __name__ == "__main__":
    # minimal self-test
    import random

    # Random small graph
    Y = {}
    R = {}
    nodes = [(i, 0) for i in range(10)]
    for a in nodes:
        outs = random.sample(nodes, k=random.randint(1, 3))
        Y[a] = set(outs)
    for a in nodes:
        R[a] = set(random.sample(nodes, k=random.randint(0, 2)))

    field = {n: random.random() for n in nodes}

    img = rasterize_relational(Y, R, field)
    save_image(img, "raster_demo.png")
    print("Wrote raster_demo.png")
