from sim import *
import matplotlib.pyplot as plt

# ----- Collatz relation modulo N -----
def collatz_step(n, N):
    x = 3 * n + 1
    while x % 2 == 0:
        x //= 2
    return x % N

def collatz_relation(N):
    pairs = [(i, collatz_step(i, N)) for i in range(N)]
    return relation_from_pairs(N, N, pairs)

# ----- Idempotence check -----
def is_idempotent(R, tol=0):
    CR = C_graph(R)
    diff = count_ones(mat_xor(R, CR))
    return diff <= tol, diff

# ----- Experiment -----
def collatz_experiment(N=20, steps=300, verbose=True):
    R = collatz_relation(N)
    Y = [row[:] for row in R]
    S_vals, sig_vals, diffs = [], [], []
    idempotent_step = None

    for k in range(steps):
        S = action_S(R, Y)
        sig = sigma_score(R, Y)
        idem, diff = is_idempotent(R)
        S_vals.append(S)
        sig_vals.append(sig)
        diffs.append(diff)
        if verbose:
            print(f"step {k:02d}: S={S:.3f}, σ={sig:.3f}, diff={diff}")

        if idem and idempotent_step is None:
            idempotent_step = k

        # comonadic evolution
        R = iterate_modal(R, 2, Y)
        Y = C_graph(Y)

    return S_vals, sig_vals, diffs, idempotent_step

# ----- Run & Plot -----
if __name__ == "__main__":
    N = 20
    steps = 30
    S_vals, sig_vals, diffs, idem_step = collatz_experiment(N, steps)

    plt.figure(figsize=(8,5))
    plt.plot(S_vals, label='Action S')
    plt.plot(sig_vals, label='σ coherence')
    if idem_step is not None:
        plt.axvline(idem_step, color='red', linestyle='--', label=f'Idempotent at {idem_step}')
    plt.xlabel('Iteration step')
    plt.ylabel('Value')
    plt.title(f'Collatz–RITM Stabilization mod {N}')
    plt.legend()
    plt.tight_layout()
    plt.show()

    if idem_step is not None:
        print(f"\nIdempotence detected at step {idem_step} (C(R)==R).")
    else:
        print("\nNo full idempotence reached within given steps.")
