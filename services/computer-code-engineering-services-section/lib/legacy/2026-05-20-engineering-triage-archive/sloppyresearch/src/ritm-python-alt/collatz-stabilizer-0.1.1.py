# RITM-Collatz Experiment Simulator
# Requires: sim.py in the same directory

from sim import *
import matplotlib.pyplot as plt

# --- Collatz relation construction ---
def collatz_pairs(n:int):
    pairs = []
    for i in range(1, n):
        if i % 2 == 0:
            j = i // 2
        else:
            j = 3 * i + 1
        if j < n:
            pairs.append((i, j))
    return pairs

# --- Simulation experiment ---
def run_collatz_experiment(n=64, steps=20, conserve_degrees=True, verbose=True):
    Y0 = line_graph(n)
    R0 = relation_from_pairs(n, n, collatz_pairs(n))

    if verbose:
        print(f"=== RITM–Collatz experiment (n={n}) ===")
    R, Y, hist = evolve_RY_noether(R0, Y0, steps=steps, conserve_degrees=conserve_degrees, verbose=verbose)

    # collect metrics
    S_vals = [S for (_,_,S,_) in hist]
    sigma_vals = [sig for (_,_,_,sig) in hist]
    return hist, S_vals, sigma_vals

# --- Visualization ---
def plot_collatz_dynamics(S_vals, sigma_vals):
    fig, ax = plt.subplots(2, 1, figsize=(6,6))
    ax[0].plot(S_vals, marker='o')
    ax[0].set_title('Action S over steps (RITM energy descent)')
    ax[0].set_xlabel('Step')
    ax[0].set_ylabel('S')

    ax[1].plot(sigma_vals, marker='o', color='green')
    ax[1].set_title('σ coherence (stabilization index)')
    ax[1].set_xlabel('Step')
    ax[1].set_ylabel('σ')
    plt.tight_layout()
    plt.show()

# --- Coalgebra extraction ---
def stabilized_indices(R, Y):
    return defect_rows(R, Y)

if __name__ == "__main__":
    hist, S_vals, sigma_vals = run_collatz_experiment(n=32, steps=15, conserve_degrees=False)
    plot_collatz_dynamics(S_vals, sigma_vals)

    Rf, Yf, Sf, sigf = hist[-1]
    stables = stabilized_indices(Rf, Yf)
    print(f"\nStabilized (coalgebra) indices: {stables}")
    print("Final topology Yf:")
    print(show_matrix(Yf))
