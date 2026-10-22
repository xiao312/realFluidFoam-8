#!/usr/bin/env python3
"""SRK equation of state and Chung et al. (1988) transport for pure O2 and CH4.

This module evaluates the property models Cavalieri et al. (2025, Int. J. Heat Mass
Transfer 251:127284) declare for their Fig. 1:

  * Soave-Redlich-Kwong equation of state with the Graboski-Daubert alpha function,
  * enthalpy and isobaric heat capacity as ideal-gas NASA7 values plus analytic SRK
    departure functions,
  * dynamic viscosity and thermal conductivity from the generalized dense-gas
    correlation of Chung, Ajlan and Lee (1988).

Every number is computed here from inspectable constants; nothing is fitted to the
figure.  Standard library only, so the module runs in the Python-only allocation.

Provenance of the constants
---------------------------
* Critical temperature, pressure, acentric factor and critical volume for O2 and CH4:
  Cavalieri et al. (2025) Table 1 (PDF page 4 of the retained copy).
* NASA7 ideal-gas coefficients and the Lennard-Jones sigma/epsilon of the independent
  kinetic-theory cross-check: the retained mechanism data file
  `replication/validation/inputs/property-thermo.inputData` (GRI30 coefficients,
  declared `Tlow 100`).  `test_srk_chung.py` re-reads that file and compares.

Model choices that the paper leaves ambiguous
---------------------------------------------
* The paper prints `0.427` in Eq. (2).  The Soave (1972) constant is 0.42748, and the
  printed `b = 0.08664 R Tc / pc` only gives the SRK critical compressibility 1/3 with
  0.42748.  `A_COEFF` is therefore 0.42748; `A_COEFF_PRINTED = 0.427` is kept so the
  sensitivity of the printed rounding can be measured instead of assumed away.
* The Chung correlation needs the ideal-gas heat capacity at constant volume for its
  Eucken-type factor.  The dilute-gas factor uses `Cv = cp0 - R`, as in the retained
  OpenFOAM implementation `src/thermophysicalModels/specie/transport/chungKinetic`.

Units
-----
SI molar throughout: J, mol, m3, K, Pa, s.  The Chung correlation is published in
g/mol, cm3/mol, poise and cal/(cm s K); the conversions are local and explicit.
"""
import math

R = 8.31446261815324          # J/(mol K)
# Chung et al. publish the correlation in thermochemical calories, so one single
# conversion is used everywhere in this module.  Round 3 mixed this with the
# International-Table value 1/4.1868 on the heat-capacity line, which biased the
# Chung cv (and hence the conductivity) by 6.7e-04 relative.
CAL_PER_JOULE = 1.0 / 4.184   # thermochemical calorie, exact by definition
R_CAL = R * CAL_PER_JOULE     # cal/(mol K) = 1.9872042586
CAL_CM_S_K_TO_W_M = 418.6798  # cal/(cm s K) -> W/(m K), as published for Eq. (12)
P_PER_CAL = 0.1               # poise -> Pa s

A_COEFF = 0.42748             # Soave (1972) attractive constant, Eq. (2)
A_COEFF_PRINTED = 0.427       # what the paper prints
B_COEFF = 0.08664             # repulsive constant, Eq. (3)

SPECIES = {
    "O2": {
        "name": "O2",
        "molar_mass": 31.9988e-3,     # kg/mol
        "Tc": 154.58,                 # K       (Cavalieri Table 1)
        "pc": 50.430e5,               # Pa      (Cavalieri Table 1, 50.430 bar)
        "omega": 0.0222,              # -       (Cavalieri Table 1)
        "vc": 73.529e-6,              # m3/mol  (Cavalieri Table 1, 73.529 cm3/mol)
        "dipole": 0.0,                # Debye   (nonpolar)
        "association": 0.0,           # kappa   (nonpolar)
        "lj_sigma": 3.458e-10,        # m       (retained dataForKineticTrans, 3.458 A)
        "lj_epsilon_k": 107.4,        # K       (retained dataForKineticTrans)
        # GRI30 NASA7, Tlow 100 K, Tcommon 1000 K
        "nasa7": (
            (3.782456360e+00, -2.996734160e-03, 9.847302010e-06, -9.681295090e-09,
             3.243728370e-12, -1.063943560e+03, 3.657675730e+00),
            (3.282537840e+00, 1.483087540e-03, -7.579666690e-07, 2.094705550e-10,
             -2.167177940e-14, -1.088457720e+03, 5.453231290e+00),
            1000.0,
        ),
    },
    "CH4": {
        "name": "CH4",
        "molar_mass": 16.0428e-3,     # kg/mol
        "Tc": 190.60,                 # K       (Cavalieri Table 1)
        "pc": 46.100e5,               # Pa      (Cavalieri Table 1, 46.100 bar)
        "omega": 0.0110,              # -       (Cavalieri Table 1)
        "vc": 98.600e-6,              # m3/mol  (Cavalieri Table 1, 98.600 cm3/mol)
        "dipole": 0.0,
        "association": 0.0,
        "lj_sigma": 3.746e-10,        # m       (retained dataForKineticTrans)
        "lj_epsilon_k": 141.4,        # K       (retained dataForKineticTrans)
        "nasa7": (
            (5.149876130e+00, -1.367097880e-02, 4.918005990e-05, -4.847430260e-08,
             1.666939560e-11, -1.024664760e+04, -4.641303760e+00),
            (7.485149500e-02, 1.339094670e-02, -5.732858090e-06, 1.222925350e-09,
             -1.018152300e-13, -9.468344590e+03, 1.843731800e+01),
            1000.0,
        ),
    },
}


class ModelError(ValueError):
    """Raised when a state point has no mechanically stable SRK root."""


# --------------------------------------------------------------------------- #
# ideal gas
# --------------------------------------------------------------------------- #
def _nasa_coeffs(species, T):
    low, high, tcommon = species["nasa7"]
    return low if T < tcommon else high


def cp_ideal(species, T):
    """Ideal-gas isobaric heat capacity, J/(mol K)."""
    a = _nasa_coeffs(species, T)
    return R * (a[0] + a[1] * T + a[2] * T ** 2 + a[3] * T ** 3 + a[4] * T ** 4)


def h_ideal(species, T):
    """Ideal-gas enthalpy relative to the NASA7 reference, J/mol."""
    a = _nasa_coeffs(species, T)
    return R * T * (a[0] + a[1] * T / 2.0 + a[2] * T ** 2 / 3.0 + a[3] * T ** 3 / 4.0
                    + a[4] * T ** 4 / 5.0 + a[5] / T)


# --------------------------------------------------------------------------- #
# SRK equation of state
# --------------------------------------------------------------------------- #
def alpha_terms(species, T, a_coeff=A_COEFF):
    """SRK a(T), da/dT and d2a/dT2 with the Graboski-Daubert alpha, per mole.

    Eq. (2) of the paper: a_k alpha_k = a_c [1 + c (1 - sqrt(T/Tc))]^2 with
    c = 0.48508 + 1.55171 omega - 0.15613 omega^2 (Eq. 4).
    """
    Tc, pc, omega = species["Tc"], species["pc"], species["omega"]
    c = 0.48508 + 1.55171 * omega - 0.15613 * omega * omega
    a_c = a_coeff * (R * Tc) ** 2 / pc
    root = math.sqrt(T / Tc)
    f = 1.0 + c * (1.0 - root)
    df = -c / (2.0 * math.sqrt(T * Tc))
    d2f = c / (4.0 * math.sqrt(Tc) * T ** 1.5)
    return a_c * f * f, 2.0 * a_c * f * df, 2.0 * a_c * (df * df + f * d2f)


def b_term(species):
    """SRK covolume b, m3/mol."""
    return B_COEFF * R * species["Tc"] / species["pc"]


def z_roots(A, B):
    """Real roots of Z^3 - Z^2 + (A - B - B^2) Z - A B = 0 (Cardano, then Newton).

    The critical isotherm makes this cubic nearly a triple root, where the closed form
    loses digits; two Newton steps on the cubic residual restore full precision.
    """
    c = A - B - B * B
    d = -A * B
    p = c - 1.0 / 3.0
    q = -2.0 / 27.0 + c / 3.0 + d
    disc = q * q / 4.0 + p * p * p / 27.0
    if disc > 1e-18:
        r = math.sqrt(disc)
        roots = [1.0 / 3.0 + _cbrt(-q / 2.0 + r) + _cbrt(-q / 2.0 - r)]
    else:
        r = math.sqrt(max(-p * p * p / 27.0, 0.0))
        if r <= 0.0:
            roots = [1.0 / 3.0]
        else:
            arg = max(-1.0, min(1.0, -q / (2.0 * r)))
            phi = math.acos(arg) / 3.0
            roots = [1.0 / 3.0 + 2.0 * r ** (1.0 / 3.0)
                     * math.cos(phi - 2.0 * math.pi * k / 3.0) for k in (0, 1, 2)]
    polished = []
    for root in roots:
        for _ in range(3):
            f = ((root - 1.0) * root + c) * root + d
            fp = (3.0 * root - 2.0) * root + c
            if fp == 0.0:
                break
            root -= f / fp
        polished.append(root)
    return polished


def _cbrt(x):
    return math.copysign(abs(x) ** (1.0 / 3.0), x)


def srk_state(species, T, p, root="stable-largest", a_coeff=A_COEFF):
    """SRK state at (T, p) for a pure species.

    Returns a dict with v [m3/mol], rho [kg/m3], Z, the departure enthalpy and heat
    capacity [J/mol, J/(mol K)], and the pressure derivatives used to build them.

    Root selection: every mechanically stable root (v > b, dp/dv < 0) is computed.
    `root` is either `'stable-largest'` (the usual gas-root convention, which is
    unambiguous when the cubic has a single real root) or `'closest:<v>'` for an
    explicit branch continuation.
    """
    if not (T > 0.0 and p > 0.0):
        raise ModelError("SRK needs T > 0 and p > 0")
    b = b_term(species)
    a, at, att = alpha_terms(species, T, a_coeff)
    A = a * p / (R * T) ** 2
    B = b * p / (R * T)

    candidates = []
    for Z in z_roots(A, B):
        if not (Z > B):
            continue
        v = Z * R * T / p
        if not (v > b):
            continue
        pv = -R * T / (v - b) ** 2 + a * (2.0 * v + b) / (v * (v + b)) ** 2
        if not (pv < 0.0):
            continue
        candidates.append((Z, v, pv))

    if not candidates:
        raise ModelError("no mechanically stable SRK root at T=%g p=%g" % (T, p))

    if root.startswith("closest:"):
        target = float(root.split(":", 1)[1])
        Z, v, pv = min(candidates, key=lambda item: abs(math.log(item[1] / target)))
    else:
        Z, v, pv = max(candidates, key=lambda item: item[1])

    pt = R / (v - b) - at / (v * (v + b))          # (dp/dT)_v
    vt = -pt / pv                                   # (dv/dT)_p
    L = math.log1p(b / v)
    C = T * at - a

    h_dep = R * T * b / (v - b) - a / (v + b) + C * L / b
    cp_dep = p * vt - R + T * att * L / b - C * vt / (v * (v + b))
    cv_dep = cp_dep + T * pt * pt / pv              # cp - cv = -T pt^2 / pv

    return {
        "T": T, "p": p, "v": v, "rho": species["molar_mass"] / v, "Z": Z,
        "a": a, "b": b, "a_t": at, "a_tt": att,
        "p_v": pv, "p_t": pt, "v_t": vt,
        "h_dep": h_dep, "cp_dep": cp_dep, "cv_dep": cv_dep,
        "n_stable_roots": len(candidates),
        "roots": [item[1] for item in candidates],
    }


def thermo_state(species, T, p, root="stable-largest", a_coeff=A_COEFF):
    """Full thermodynamic state: rho, h, cp, cv, s-departure-free quantities."""
    state = srk_state(species, T, p, root=root, a_coeff=a_coeff)
    cp0 = cp_ideal(species, T)
    h0 = h_ideal(species, T)
    state.update({
        "cp_ideal": cp0,
        "h_ideal": h0,
        "cv_ideal": cp0 - R,
        "cp": cp0 + state["cp_dep"],
        "cv": cp0 - R + state["cv_dep"],
        "h": h0 + state["h_dep"],
    })
    return state


# --------------------------------------------------------------------------- #
# Chung, Ajlan and Lee (1988) dense-gas transport
# --------------------------------------------------------------------------- #
# Table II of Chung et al. (1988), viscosity: A_i = a0 + a1 w + a2 mu_r^4 + a3 kappa.
_A0 = (6.32402, 0.0012102, 5.28346, 6.62263, 19.74540,
       -1.89992, 24.27450, 0.79716, -0.23816, 0.068629)
_A1 = (50.41190, -0.0011536, 254.209, 38.0957, 7.63034,
       -12.53670, 3.44945, 1.11764, 0.067695, 0.34793)
_A2 = (-51.68, -0.0062571, -168.481, -8.46414, -14.35440,
       4.98529, -11.29130, 0.012348, -0.8163, 0.59256)
_A3 = (1189.02, 0.037283, 3898.270, 31.4178, 31.52670,
       -18.1507, 69.3464, -4.1161, 4.02528, -0.72663)
# Table IV of Chung et al. (1988), thermal conductivity: same combination for B_i.
_B0 = (2.41657, -0.50924, 6.61069, 14.54250, 0.79274, -5.8634, 81.171)
_B1 = (0.74824, -1.50936, 5.62073, -8.91387, 0.82019, 12.8005, 114.1580)
_B2 = (-0.91858, -49.99120, 64.7599, -5.63794, -0.69369, 9.58926, -60.841)
_B3 = (121.721, 69.9834, 27.0389, 74.3435, 6.31734, -65.5292, 466.7750)


def _coefficients(rows, omega, mu_r4, kappa):
    a0, a1, a2, a3 = rows
    return [a0[i] + a1[i] * omega + a2[i] * mu_r4 + a3[i] * kappa
            for i in range(len(a0))]


def _exp_ratio(y, k):
    """(1 - exp(-k y)) / y with its y -> 0 limit k."""
    if y < 1e-14:
        return k
    return (1.0 - math.exp(-k * y)) / y


def chung_dilute(species, T):
    """Dilute-gas part of the Chung correlation: T*, Omega*, mu_r, Fc, eta0 [P]."""
    Tc, omega = species["Tc"], species["omega"]
    t_star = 1.2593 * T / Tc                      # Eq. (3)
    mu_r = 131.3 * species["dipole"] / math.sqrt(species["vc"] * 1e6 * Tc)   # Eq. (8)
    fc = 1.0 - 0.2756 * omega + 0.059035 * mu_r ** 4 + species["association"]
    omega_star = (1.16145 * t_star ** -0.14874
                  + 0.52487 * math.exp(-0.7732 * t_star)
                  + 2.16178 * math.exp(-2.43787 * t_star)
                  + (-6.435e-4) * t_star ** 0.14874
                  * math.sin(18.0323 * t_star ** -0.76830 - 7.27371))
    m_gmol = species["molar_mass"] * 1e3
    vc_cm3 = species["vc"] * 1e6
    eta0 = (4.0785e-5 * math.sqrt(m_gmol * T) * fc
            / (omega_star * vc_cm3 ** (2.0 / 3.0)))          # poise
    return {"t_star": t_star, "mu_r": mu_r, "fc": fc,
            "omega_star": omega_star, "eta0": eta0}


def chung_state(species, T, p, rho=None, cp_ideal_value=None, a_coeff=A_COEFF):
    """Viscosity [Pa s] and thermal conductivity [W/(m K)] of Chung et al. (1988).

    `rho` comes from the SRK state, so the dense-gas correction Y = rho Vc / 6 is
    evaluated with the same density the figure plots.
    """
    if rho is None:
        rho = srk_state(species, T, p, a_coeff=a_coeff)["rho"]
    if cp_ideal_value is None:
        cp_ideal_value = cp_ideal(species, T)
    dilute = chung_dilute(species, T)
    t_star, mu_r, eta0 = dilute["t_star"], dilute["mu_r"], dilute["eta0"]
    omega = species["omega"]
    kappa = species["association"]
    m_gmol = species["molar_mass"] * 1e3
    vc_cm3 = species["vc"] * 1e6
    mu_r4 = mu_r ** 4

    rho_mol_cm3 = rho / species["molar_mass"] / 1e6     # mol/cm3
    y = rho_mol_cm3 * vc_cm3 / 6.0                      # Eq. (10) density variable
    if y >= 1.0:
        raise ModelError("Chung density variable Y=%g outside the correlation" % y)
    g1 = (1.0 - 0.5 * y) / (1.0 - y) ** 3               # Eq. (10)

    ma = _coefficients((_A0, _A1, _A2, _A3), omega, mu_r4, kappa)
    g2 = ((ma[0] * _exp_ratio(y, ma[3]) + ma[1] * g1 * math.exp(ma[4] * y)
           + ma[2] * g1) / (ma[0] * ma[3] + ma[1] + ma[2]))
    eta_k = eta0 * (1.0 / g2 + ma[5] * y)
    eta_p = ((40.785e-6 / math.sqrt(t_star)) * math.sqrt(m_gmol * T)
             / vc_cm3 ** (2.0 / 3.0) * ma[6] * y * y * g2
             * math.exp(ma[7] + ma[8] / t_star + ma[9] / t_star ** 2))
    mu = P_PER_CAL * (eta_k + eta_p)                    # poise -> Pa s

    mb = _coefficients((_B0, _B1, _B2, _B3), omega, mu_r4, kappa)
    cv_cal = (cp_ideal_value - R) * CAL_PER_JOULE        # J/(mol K) -> cal/(mol K)
    alpha = cv_cal / R_CAL - 1.5                        # Eq. (9)
    beta = 0.7862 - 0.7109 * omega + 1.1368 * omega * omega
    tr = T / species["Tc"]
    z = 2.0 + 10.5 * tr * tr
    psi = (1.0 + alpha * (0.215 + 0.28288 * alpha - 1.061 * beta + 0.26665 * z)
           / (0.6366 + beta * z + 1.061 * alpha * beta))
    lam0 = 7.452 * (eta0 / m_gmol) * psi                # cal/(cm s K)
    h2 = ((mb[0] * _exp_ratio(y, mb[3]) + mb[1] * g1 * math.exp(mb[4] * y)
           + mb[2] * g1) / (mb[0] * mb[3] + mb[1] + mb[2]))
    lam_k = lam0 * (1.0 / h2 + mb[5] * y)
    lam_p = (3.039e-4 * math.sqrt(species["Tc"] / m_gmol) / vc_cm3 ** (2.0 / 3.0)
             * mb[6] * y * y * h2 * math.sqrt(tr))
    kappa_cond = CAL_CM_S_K_TO_W_M * (lam_k + lam_p)

    return {"mu": mu, "kappa": kappa_cond, "y": y, "g1": g1, "g2": g2, "h2": h2,
            "psi": psi, "alpha_eucken": alpha, "lambda0": lam0,
            "lambda_k": lam_k, "lambda_p": lam_p,
            "t_star": t_star, "omega_star": dilute["omega_star"],
            "eta0": eta0, "fc": dilute["fc"], "mu_r": dilute["mu_r"]}


# --------------------------------------------------------------------------- #
# independent cross-checks (different correlations, different parameters)
# --------------------------------------------------------------------------- #
def kinetic_viscosity(species, T):
    """Chapman-Enskog viscosity from the species Lennard-Jones parameters, Pa s."""
    t_star = T / species["lj_epsilon_k"]
    omega_v = (1.16145 * t_star ** -0.14874 + 0.52487 * math.exp(-0.7732 * t_star)
               + 2.16178 * math.exp(-2.43787 * t_star))
    sigma_angstrom = species["lj_sigma"] * 1e10
    m_gmol = species["molar_mass"] * 1e3
    return 2.6693e-6 * math.sqrt(m_gmol * T) / (sigma_angstrom ** 2 * omega_v)


def eucken_conductivity(species, T, mu, cp_value=None):
    """Classical Eucken estimate, W/(m K): lambda = mu (cv + 9R/4) / M.

    Eucken is the natural independent check: it needs only cv, the same dilute
    viscosity and the molar mass, so it shares no coefficient with Chung's Table IV.
    It is a rough correlation (few per cent here), not a replacement.
    """
    if cp_value is None:
        cp_value = cp_ideal(species, T)
    return mu * ((cp_value - R) + 2.25 * R) / species["molar_mass"]
