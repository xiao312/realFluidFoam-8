"""Independent molar-SI SRK checks; no OpenFOAM or transport dependency."""
import math
import re

import numpy as np

R = 8.31446261815324  # J/(mol K); dictionary Pc is MPa.
OMEGA_B = (2 ** (1 / 3) - 1) / 3
OMEGA_A = 1 / (9 * (2 ** (1 / 3) - 1))
CRITICAL_RATIO = OMEGA_A / OMEGA_B


def read_species(path):
    text = path.read_text()
    result = {}
    for name in ("H2", "CH4", "O2", "N2"):
        match = re.search(r"(?m)^" + name + r"\s*\{", text)
        if not match:
            raise ValueError("Missing species " + name)
        start = text.index("{", match.start())
        depth = 0
        for end in range(start, len(text)):
            depth += (text[end] == "{") - (text[end] == "}")
            if depth == 0:
                break
        else:
            raise ValueError("Unclosed species " + name)
        block = text[start:end + 1]
        result[name] = {}
        for key in ("Tc", "Pc", "omega", "molWeight", "Vc"):
            value = re.search(r"\b" + key + r"\s+([-+\d.eE]+)\s*;", block)
            if not value:
                raise ValueError("Missing " + name + "/" + key)
            result[name][key] = float(value[1])
        result[name]["Pc"] *= 1e6
    return result


def composition(fuel, phi, nitrogen_per_oxygen=79 / 21):
    if fuel not in ("H2", "CH4") or phi <= 0 or nitrogen_per_oxygen < 0:
        raise ValueError("Expected H2/CH4, positive phi and nonnegative N2/O2")
    oxygen = .5 if fuel == "H2" else 2.
    amounts = np.array([phi, oxygen, oxygen * nitrogen_per_oxygen])
    return amounts / sum(amounts)


def coefficients(species, fuel, x, alpha="fork", volume="critical-pressure"):
    """Build pure species arrays. Mixture a(T) is calculated separately."""
    if not np.isfinite(x).all() or min(x) < 0 or abs(sum(x) - 1) > 1e-12:
        raise ValueError("Expected normalized, finite, nonnegative mole fractions")
    rows = [species[name] for name in (fuel, "O2", "N2")]
    tc = np.array([s["Tc"] for s in rows])
    pc = np.array([s["Pc"] for s in rows])
    omega = np.array([s["omega"] for s in rows])
    b = .08664 * R * tc / pc
    if volume == "measured-volume":
        # Diagnostic: forcing SRK critical volume to the tabulated real Vc.
        b = np.array([s["Vc"] for s in rows]) * 1e-6 / (1 + 2**(1/3) + 4**(1/3))
    elif volume != "critical-pressure":
        raise ValueError("Unknown volume rule")
    ac = .42747 * (R * tc)**2 / pc
    if alpha == "fork":
        slope = .48508 + 1.5517 * omega - .15613 * omega**2
    elif alpha == "original-soave":
        slope = .48 + 1.574 * omega - .176 * omega**2
    elif alpha == "constant":
        slope = np.zeros(3)
    else:
        raise ValueError("Unknown alpha rule")
    return dict(x=np.array(x), tc=tc, ac=ac, slope=slope, bi=b, b=float(x @ b))


def attraction(temperature, model):
    """Direct double sum, independent of the native expanded-polynomial path."""
    bracket = 1 + model["slope"] * (1 - np.sqrt(temperature / model["tc"]))
    if min(bracket) <= 0:
        raise ValueError("Outside the positive Soave square-root branch")
    pure = model["ac"] * bracket**2
    return sum(model["x"][i] * model["x"][j] * math.sqrt(pure[i] * pure[j])
               for i in range(3) for j in range(3))


def analytical(model):
    b = model["b"]
    intercept = model["x"] @ (np.sqrt(model["ac"]) * (1 + model["slope"]))
    slope = model["x"] @ (np.sqrt(model["ac"]) * model["slope"] / np.sqrt(model["tc"]))
    temperature = (intercept / (slope + math.sqrt(CRITICAL_RATIO * R * b)))**2
    volume = (1 + 2**(1/3) + 4**(1/3)) * b
    pressure = OMEGA_B * R * temperature / b
    return dict(Tc_K=float(temperature), Pc_atm=float(pressure / 101325),
                b_cm3_mol=b * 1e6, vc_cm3_mol=volume * 1e6,
                A=float(intercept), C=float(slope))


def numerical_inflection(model, step=.01):
    """Solve two finite-difference pressure derivatives; no critical constants.

    Variables are T and u=v/b. Five-point derivatives act on p*b/(R*T).
    Newton updates use a numerical Jacobian. Failure is explicit.
    """
    def derivatives(state):
        temperature, u = state
        if temperature <= 0 or u <= 1 + 2 * step:
            raise ValueError("Inflection iteration left the physical domain")
        attraction_ratio = attraction(temperature, model) / (R * temperature * model["b"])
        def pressure(q):
            return 1 / (q - 1) - attraction_ratio / (q * (q + 1))
        p = [pressure(u + k * step) for k in (-2, -1, 0, 1, 2)]
        return np.array([(p[0] - 8*p[1] + 8*p[3] - p[4]) / (12 * step),
                         (-p[0] + 16*p[1] - 30*p[2] + 16*p[3] - p[4]) / (12 * step**2)])
    state = np.array([120., 4.])
    for iteration in range(30):
        residual = derivatives(state)
        if max(abs(residual)) < 2e-10:
            break
        columns = []
        for index, delta in enumerate((.01, .001)):
            change = np.zeros(2)
            change[index] = delta
            columns.append((derivatives(state + change) - derivatives(state - change)) / (2*delta))
        state -= np.linalg.solve(np.column_stack(columns), residual)
    else:
        raise ValueError("Numerical pressure inflection did not converge")
    temperature, u = state
    v = u * model["b"]
    pressure = R * temperature / (v - model["b"]) - attraction(temperature, model) / (v * (v + model["b"]))
    return dict(Tc_K=float(temperature), Pc_atm=float(pressure / 101325),
                vc_cm3_mol=float(v * 1e6), residual=float(max(abs(residual))),
                iterations=iteration + 1)
