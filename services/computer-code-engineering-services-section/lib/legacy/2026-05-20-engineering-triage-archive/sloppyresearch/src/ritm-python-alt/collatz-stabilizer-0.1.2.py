# RITM-Collatz Experiment Simulator (Stepwise Comonadic Version)
# Requires: sim.py in the same directory

from sim import *
import matplotlib.pyplot as plt

# --- Stepwise comonadic operators ---
def box_step(A: List[List[int]], steps:int=1) -> List[List[int]]:
    n = len(A)
    C = [row[:] for row in A]
    for _ in range(steps):
        C_next = mat_bool_or(C, mat_bool_mul(C, A))
        for i in range(n):
            C_next[i][i] = 1  # ensure reflexivity
        C = C_next
    return C

def diamond_step(A: List[List[int]], steps:int=1) -> List[List[int]]:
    return transpose(box_step(transpose(A), steps=steps))

def C_graph_step(A: List[List[int]], steps:int=1) -> List[List[int]]:
    return box_step(diamond_step(A, steps=steps), steps=steps)

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

# --- Stepwise evolve ---
def evolve_RY_stepwise(R, Y, steps=10, closure_step=1, verbose=True):
    hist = []
    for t in range(steps):
        CY = C_graph_step(Y, steps=closure_step)
        Rn = mat_bool_mul(R, CY)
        Yn = mat_bool_or(Y, CY)
        S = action_S(Rn, Yn)
        sig = sigma_score(Rn, Yn)
        if verbose:
            print(f"t={t:02d}  S={S:.3f}  σ={sig:.3f}")
        hist.append((Rn, Yn, S, sig))
        if t>0 and abs(hist[-1][2]-hist[-2][2])<1e-9:
            break
        R, Y = Rn, Yn
    return hist

# --- Experiment driver ---
def run_collatz_experiment_stepwise(n=32, steps=10, closure_step=1, verbose=True):
    Y0 = line_graph(n)
    R0 = relation_from_pairs(n, n, collatz_pairs(n))
    hist = evolve_RY_stepwise(R0, Y0, steps=steps, closure_step=closure_step, verbose=verbose)
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
    hist, S_vals, sigma_vals = run_collatz_experiment_stepwise(n=32, steps=15, closure_step=1)
    plot_collatz_dynamics(S_vals, sigma_vals)
    Rf, Yf, Sf, sigf = hist[-1]
    print(f"\nStabilized indices: {stabilized_indices(Rf, Yf)}")
