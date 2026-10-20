"""Numerical profile checks shared without a PDF/plotting dependency."""
import numpy as np


def profile_diagnostics(result):
    data = np.genfromtxt(result/"profile.csv", delimiter=",", names=True)
    species = [name for name in data.dtype.names if name.startswith("Y_")]
    if not species or len(data) < 3:
        raise ValueError(f"Incomplete profile: {result}")
    if not all(np.isfinite(data[name]).all() for name in data.dtype.names):
        raise ValueError(f"Nonfinite profile: {result}")
    mass_flux = data["rho_kg_m3"]*data["U_m_s"]
    return {
        "points": len(data),
        "min_temperature_K": float(min(data["T_K"])),
        "max_temperature_K": float(max(data["T_K"])),
        "max_species_sum_error": float(max(abs(sum(data[s] for s in species)-1))),
        "minimum_mass_fraction": float(min(min(data[s]) for s in species)),
        "max_relative_massflux_change": float(max(abs(mass_flux/mass_flux[0]-1))),
        "inlet_outlet_enthalpy_difference_J_kg": float(data["h_J_kg"][-1]-data["h_J_kg"][0]),
    }
