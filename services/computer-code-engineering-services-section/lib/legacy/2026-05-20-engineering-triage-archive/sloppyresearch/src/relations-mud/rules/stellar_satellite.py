# ------------------ ORBITAL ------------------

def orbital_period_years(a_AU: float, M_star_sun: float) -> float:
    """
    Kepler's 3rd law (in AU/yr/solar-mass units, neglecting planet mass).
    """
    return math.sqrt(a_AU ** 3 / max(1e-6, M_star_sun))


def hill_radius_AU(a_AU: float, M_p_earth: float, M_star_sun: float) -> float:
    """
    Approximate Hill radius (gravitational sphere of influence) in AU.
    """
    M_p_sun = M_p_earth / 332946.0
    return a_AU * (M_p_sun / (3 * M_star_sun)) ** (1 / 3)


def orbital_insolation_scaling(L_Lsun: float, a_AU: float) -> float:
    """
    Dimensionless scaling factor (S/S0) = (L/Lsun) / (a/AU)^2
    """
    return L_Lsun / (a_AU ** 2)
