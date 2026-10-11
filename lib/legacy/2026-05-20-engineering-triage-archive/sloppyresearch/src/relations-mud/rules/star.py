import math

# ------------------ STELLAR ------------------

def luminosity_from_mass(M_sun: float) -> float:
    """
    Compute stellar luminosity L/Lsun from main-sequence mass–luminosity relation.
    """
    if M_sun < 0.43:
        return M_sun ** 2.3
    elif M_sun < 2.0:
        return M_sun ** 4.0
    else:
        return M_sun ** 3.5


def radius_from_mass(M_sun: float) -> float:
    """
    Approximate stellar radius R/Rsun for main-sequence stars.
    """
    return max(0.1, M_sun ** 0.8)


def temperature_from_LR(L_Lsun: float, R_Rsun: float) -> float:
    """
    Compute stellar effective temperature (K) from luminosity and radius.
    """
    SIGMA = 5.670374419e-8
    L = L_Lsun * 3.828e26
    R = R_Rsun * 6.957e8
    return (L / (4 * math.pi * R ** 2 * SIGMA)) ** 0.25


def habitable_zone_distance(L_Lsun: float) -> float:
    """
    Simple habitable zone midpoint distance in AU.
    """
    return math.sqrt(L_Lsun)
