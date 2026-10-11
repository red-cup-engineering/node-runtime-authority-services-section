# save as simulate_transition_nobreak.py next to sim.py
import os
import imageio.v2 as imageio
import matplotlib.pyplot as plt
from sim import (line_graph, relation_from_pairs, C_graph, mat_bool_mul,
                 mat_bool_or, transpose, group_orbit_boolean_average,
                 realize_digraph_with_preferences, action_S, sigma_score,
                 count_ones)

import random

def evolve_no_break(R, Y, steps=20, conserve_degrees=False, group_perms=None):
    # identical dynamics to evolve_RY_noether, but without the early-stopping check
    # and with degree/symmetry projection options preserved
    def indeg_outdeg(Y):
        n = len(Y)
        outd = [sum(Y[i][j] for j in range(n)) for i in range(n)]
        indeg = [sum(Y[i][j] for i in range(n)) for j in range(n)]
        edges = sum(outd)
        return indeg, outd, edges

    indeg0, outdeg0, _ = indeg_outdeg(Y)
    hist = []
    for _ in range(steps):
        CY    = C_graph(Y)
        Rn    = mat_bool_mul(R, CY)
        Yprop = mat_bool_or(CY, mat_bool_mul(transpose(R), R))
        if group_perms is not None:
            Yprop = group_orbit_boolean_average(Yprop, group_perms)
        Yn = realize_digraph_with_preferences(indeg0, outdeg0, Yprop) if conserve_degrees else Yprop
        if group_perms is not None:
            Yn = group_orbit_boolean_average(Yn, group_perms)
            Yn = realize_digraph_with_preferences(indeg0, outdeg0, Yn) if conserve_degrees else Yn
        S = action_S(Rn, Yn); sig = sigma_score(Rn, Yn)
        hist.append((Rn, Yn, S, sig))
        R, Y = Rn, Yn
    return hist

def render_gif(n=40, steps=20, outdir="frames", gif_path="quantum_to_classical_transition_nobreak.gif"):
    os.makedirs(outdir, exist_ok=True)
    Y0 = line_graph(n)
    pairs = [(i,i) for i in range(n)] + [(i,(i+1)%n) for i in range(n)]
    for _ in range(int(n*n*0.03)):     # 3 % random extras
        i, j = random.randrange(n), random.randrange(n)
        pairs.append((i, j))
    R0 = relation_from_pairs(n, n, pairs)
    hist = evolve_no_break(R0, Y0, steps=steps, conserve_degrees=False, group_perms=None)
    frames = []
    for t, (Rt, _, _, _) in enumerate(hist):
        fig, ax = plt.subplots(figsize=(6,6))
        ax.imshow(Rt, cmap="Greys", interpolation="nearest")
        density = count_ones(Rt)/(n*n)
        ax.set_title("Quantum → Classical Transition (XOR → OR)")
        ax.text(0.5, 1.02, f"λ={t:02d}, density={density:.2f}", transform=ax.transAxes,
                ha="center", color="blue")
        ax.set_xlabel("Y (codomain)")
        ax.set_ylabel("X (domain)")
        fig.tight_layout()
        frame_path = os.path.join(outdir, f"frame_{t:02d}.png")
        fig.savefig(frame_path, dpi=150); plt.close(fig)
        frames.append(frame_path)
    imageio.mimsave(gif_path, [imageio.imread(f) for f in frames], duration=0.25)
    return gif_path

if __name__ == "__main__":
    print(render_gif())
