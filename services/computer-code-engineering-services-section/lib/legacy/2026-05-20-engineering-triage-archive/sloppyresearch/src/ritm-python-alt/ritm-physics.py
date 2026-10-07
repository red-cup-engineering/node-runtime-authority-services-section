# ritm_physics_simulator.py — live physics layer over the RITM core
# Evolves the comonadic event engine, measures (S,σ) until stability ≥ X,
# and plots the results.

import matplotlib.pyplot as plt
from typing import Dict, Set, Tuple, Optional
from math import isfinite

# ---------- import the RITM core ----------
from events import step_event, seed_one_arrow, YAdj, RRel, Node

# ---------- run-and-measure loop ----------

def measures_linear(
    R: RRel, Y: YAdj, *, use_C_closure: bool = True
) -> Tuple[float, float]:
    rho, dom_nodes, cod_nodes = linear_reflection_rho(R, Y, use_C_closure=use_C_closure)
    R_dense = dense_from_R(dom_nodes, cod_nodes, R)  # for σ denominator
    S = action_S_linear(rho)
    σ = sigma_coherence_linear(rho, R_dense)
    return S, σ

def evolve_to_stability(
    Y: YAdj,
    R: RRel,
    *,
    stability_threshold: float = 1.0,
    snapshot_interval: int = 10,
    step_limit: int = 500,
    use_C_closure: bool = True
):
    """
    Evolve the RITM world until coherence σ ≥ stability_threshold
    or until step_limit reached.
    Returns lists of step numbers, S, σ for plotting.
    """
    steps, Ss, sigmas = [], [], []
    print(f"--- evolve up to {step_limit} steps (snapshot every {snapshot_interval}) ---")

    for k in range(step_limit):
        ev = step_event(R, Y, prefer="Cδ")
        if ev is None:
            print("No further events (δ disabled?)")
            break

        kind, a, b, src = ev
        print(f"{k:03d}: {kind} {a}->{b} [{src}]")

        if (k + 1) % snapshot_interval == 0:
            S, σ = measures_linear(R, Y, use_C_closure=use_C_closure)
            steps.append(k + 1)
            Ss.append(S)
            sigmas.append(σ)
            print(f"   snapshot @{k+1}: S={S:.4f}, σ={σ:.4f}")
            if σ >= stability_threshold:
                print(f"Reached stability σ≥{stability_threshold:.3f} at step {k+1}")
                break

    return steps, Ss, sigmas

# ---------- visualization ----------

def plot_history(steps, S_values, sigma_values):
    plt.figure(figsize=(8,5))
    plt.plot(steps, S_values, label="Action S", marker="o")
    plt.plot(steps, sigma_values, label="Coherence σ", marker="s")
    plt.xlabel("Step")
    plt.ylabel("Value")
    plt.title("RITM Physics Evolution")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# ---------- startup configurations ----------

def load_startup_config(mode: str = "one_arrow") -> Tuple[YAdj, RRel]:
    """
    Convenience wrapper for different initial conditions.
    mode = "one_arrow"  : single arrow 0→1 (default)
    mode = "triangle"   : small three-object ring
    """
    if mode == "triangle":
        # a richer base
        Y: YAdj = {
            (0,0): {(0,0), (1,0)},
            (1,0): {(1,0), (2,0)},
            (2,0): {(2,0), (0,0)},
        }
        R: RRel = {
            (0,0): {(1,0)},
            (1,0): {(2,0)},
            (2,0): {(0,0)},
        }
        return Y, R
    # default: one arrow seed
    return seed_one_arrow(0, 1)

# ---------- demo ----------

if __name__ == "__main__":
    # choose configuration and parameters
    Y, R = load_startup_config("one_arrow")
    steps, S_vals, sigma_vals = evolve_to_stability(
        Y, R,
        stability_threshold=1.0,   # stop when coherence ≥ 1.0
        snapshot_interval=10,
        step_limit=200
    )

    if steps:
        plot_history(steps, S_vals, sigma_vals)
    else:
        print("No snapshots taken.")
