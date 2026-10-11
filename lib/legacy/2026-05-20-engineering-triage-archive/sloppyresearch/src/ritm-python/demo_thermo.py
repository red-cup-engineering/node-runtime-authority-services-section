# demo_thermo_loop.py
"""
Toy thermal-flow simulation running on your geometry / physics / thermo stack.
"""

import time
from category import seed_object
from geometry import from_relational_object
from physics import ScalarField, VectorField, visualize_ascii
from thermo import (
    heat_step, project_incompressible,
    ideal_gas_pressure, clausius_clapeyron,
    total_mass, entropy_proxy
)

# ---------------------------------------------------------------------
# 1. Build a geometric chart
# ---------------------------------------------------------------------
X = seed_object(0, 1)
G = from_relational_object(X)

ys = [p.y for p in G.points.values()]
ymin, ymax = min(ys), max(ys)
yrange = ymax - ymin if ymax != ymin else 1.0

# ---------------------------------------------------------------------
# 2. Initial fields
# ---------------------------------------------------------------------
# temperature: warmer at bottom
T = ScalarField({
    n: 290.0 + 10.0 * (1.0 - (p.y - ymin) / yrange)
    for n, p in G.points.items()
})

# density: exponential decay with altitude
rho0 = 1.2
H = yrange / 2.0
rho = ScalarField({
    n: rho0 * (2.71828 ** (-(p.y - ymin) / H))
    for n, p in G.points.items()
})

# horizontal flow
u = VectorField({n: (0.2, 0.0) for n in G.points})

# ---------------------------------------------------------------------
# 3. Derived thermo fields
# ---------------------------------------------------------------------
p = ideal_gas_pressure(rho, T)
es = clausius_clapeyron(T)

# ---------------------------------------------------------------------
# 4. Time integration loop
# ---------------------------------------------------------------------
dt = 0.1
kappa = 0.05
steps = 20

print("Starting toy heat transport simulation:")
print("Nodes:", len(G.points), "\n")

for step in range(steps):
    # temperature evolution
    T = heat_step(G, T, u, dt=dt, kappa=kappa)
    # incompressible projection (velocity correction)
    u, p_dyn = project_incompressible(G, u, iters=20, alpha=0.3)

    # simple diagnostics
    ent = entropy_proxy(T)
    mass = total_mass(rho)
    print(f"Step {step:02d}: entropy={ent:8.3f}  mass={mass:6.2f}")

    # visualize temperature field
    visualize_ascii(G)
    time.sleep(0.2)

print("Simulation complete.")
