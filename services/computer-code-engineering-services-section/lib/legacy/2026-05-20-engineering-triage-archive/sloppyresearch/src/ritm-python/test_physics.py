"""
tests_physics.py — Smoke tests for physics.py and cohesive geometry stack.

These tests ensure:
- Finite, non-NaN total energy after simulation steps
- Node and edge counts remain bounded under cohesive functors
- Gradient/divergence/Laplacian operators behave stably
- Pullback and integration steps terminate in finite time

Run:
    python tests_physics.py
or with pytest:
    pytest -q tests_physics.py
"""

import math
from physics import (
    from_relational_object, visualize_ascii,
    ScalarField, VectorField,
    gradient, divergence, laplacian,
    total_energy, semi_implicit_step,
    spring_potential_gradient,
    pullback_scalar, pullback_vector,
    BOX_GEO
)
from category import seed_object

TOL = 1e-8

def test_energy_stability():
    """Energy stays finite and nonnegative after a few steps."""
    X = seed_object(0, 1)
    G = from_relational_object(X)
    phi = ScalarField({n: 1.0 for n in G.points})
    v = VectorField({n: (0.1, 0.0) for n in G.points})

    Gf, phi_f = pullback_scalar(BOX_GEO, G, phi)
    _, v_f = pullback_vector(BOX_GEO, G, v)

    E0 = total_energy(Gf, v_f, phi_f)
    Gt, vt = Gf, v_f
    for _ in range(5):
        Gt, vt = semi_implicit_step(
            Gt, vt, phi_f,
            grad_potential=lambda c, p: spring_potential_gradient(c, p, k=0.5),
            dt=0.1
        )
    Ef = total_energy(Gt, vt, phi_f)

    assert not math.isnan(E0) and not math.isnan(Ef)
    assert Ef >= 0 and E0 >= 0
    assert abs(Ef - E0) / (E0 + TOL) < 0.5, "Energy drift too large"


def test_grad_div_laplacian():
    """Gradient/divergence/Laplacian return correct shapes and finite values."""
    X = seed_object(0, 1)
    G = from_relational_object(X)
    phi = ScalarField({n: 1.0 for n in G.points})
    grad = gradient(G, phi)
    div = divergence(G, grad)
    lap = laplacian(G, phi)

    assert set(grad.data.keys()) == set(G.points.keys())
    assert set(div.data.keys()) == set(G.points.keys())
    assert set(lap.data.keys()) == set(G.points.keys())
    assert all(math.isfinite(vx) and math.isfinite(vy) for vx, vy in grad.data.values())
    assert all(math.isfinite(val) for val in div.data.values())
    assert all(math.isfinite(val) for val in lap.data.values())


def test_pullback_bounded():
    """Pullbacks through BOX_GEO don’t create infinite growth."""
    X = seed_object(0, 1)
    G = from_relational_object(X)
    phi = ScalarField({n: 1.0 for n in G.points})
    v = VectorField({n: (0.0, 0.0) for n in G.points})

    Gp, phip = pullback_scalar(BOX_GEO, G, phi)
    _, vp = pullback_vector(BOX_GEO, G, v)

    assert len(Gp.points) < 20, "BOX_GEO generated too many points"
    assert all(math.isfinite(val) for val in phip.data.values())
    assert all(math.isfinite(vx) and math.isfinite(vy) for vx, vy in vp.data.values())


def test_ascii_visualization_runs():
    """visualize_ascii() produces output and terminates."""
    X = seed_object(0, 1)
    G = from_relational_object(X)
    out = visualize_ascii(G)
    assert isinstance(out, str)
    assert "->" in out


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            print(f"Running {name} ...", end="")
            fn()
            print(" ok")
    print("All physics tests passed.")
    
