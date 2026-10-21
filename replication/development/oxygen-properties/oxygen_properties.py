#!/usr/bin/env python3
"""Peng-Robinson and Abudour volume-translated PR properties for pure oxygen.

Implements Eqs. (8)-(13) of Mueller & Pfitzner (2015), EUCASS 2015 paper 018, as
used in their Figure 1 verification of real-gas thermodynamics for O2 at
p = 5.61 MPa (a: density, b: cp). Python standard library only.

Model (symbols as printed; see README.md for provenance of every constant):
  p   = R T/(v_PR-b) - a/(v_PR^2 + 2 v_PR b - b^2)                        (8)
  a(T)= 0.45724 R^2 Tc^2/pc * alpha(T),  alpha = [1+kappa(1-sqrt(T/Tc))]^2
  b   = 0.07780 R Tc/pc,  kappa = 0.37464 + 1.54226 w - 0.26992 w^2
  v_m = v_PR + c_m + dc_m (0.35/(0.35+d_m))                              (9)
  c_m = (R Tc/pc)[c1 - (0.004+c1) exp(-2 d_m)]                           (10)
  c1  = 0.4266 Zc_exp - 0.1101   Eq. (12) evaluated with the experimental Zc,
                                  see critical_tolerance.py and README.md
  d_m = -(v_PR^2/(R Tc)) (dp/dv_PR)|_T                                   (13)
  dc_m= (R Tc/pc)(Zc_exp - Zc_PR)   critical-volume offset, see README.

Caloric properties use the *uncorrected* PR volume because the paper states
"we use the uncorrected PR EoS in the evaluation of the caloric properties",
so cp carries no volume-translation term.

Units: SI internally (Pa, m^3/mol, K, J/(mol K)); rho in kg/m^3, cp in J/(kg K).
"""

import math

R = 8.314462618          # J/(mol K), CODATA 2018
M_O2 = 0.0319988         # kg/mol
P_FIG1 = 5.61e6          # Pa, Figure 1 pressure

# Critical constants of O2, NIST Chemistry WebBook / Poling et al. standard set.
TC = 154.581             # K
PC = 5.043e6             # Pa
OMEGA = 0.022
ZC_PR = 0.3074           # PR critical compressibility, the universal PR value
ZC_EXP = 0.288           # experimental critical compressibility of O2

KAPPA = 0.37464 + 1.54226 * OMEGA - 0.26992 * OMEGA ** 2
B_PR = 0.07780 * R * TC / PC
SQ2 = math.sqrt(2.0)

# NIST Shomate ideal-gas cp for O2, 100-700 K (t = T/1000), J/(mol K).
SHOMATE = (31.32234, -20.23531, 57.86644, -36.50624, -0.007374)


def _cbrt(x):
    return math.copysign(abs(x) ** (1.0 / 3.0), x)


def cubic_roots(a3, a2, a1, a0):
    """Real roots of a3 z^3 + a2 z^2 + a1 z + a0 (trigonometric method)."""
    b, c, d = a2 / a3, a1 / a3, a0 / a3
    q = (3.0 * c - b * b) / 9.0
    r = (9.0 * b * c - 27.0 * d - 2.0 * b ** 3) / 54.0
    disc = q ** 3 + r * r
    if disc > 0.0:
        sq = math.sqrt(disc)
        return [_cbrt(r + sq) + _cbrt(r - sq) - b / 3.0]
    theta = math.acos(max(-1.0, min(1.0, r / math.sqrt(-q ** 3))))
    s = 2.0 * math.sqrt(-q)
    return [s * math.cos((theta + 2.0 * k * math.pi) / 3.0) - b / 3.0 for k in range(3)]


def alpha(T):
    return (1.0 + KAPPA * (1.0 - math.sqrt(T / TC))) ** 2


def pr_a(T):
    return 0.45724 * R * R * TC * TC / PC * alpha(T)


def pr_da_dT(T):
    f = 1.0 + KAPPA * (1.0 - math.sqrt(T / TC))
    return 0.45724 * R * R * TC * TC / PC * 2.0 * f * (-KAPPA / (2.0 * math.sqrt(T * TC)))


def pr_d2a_dT2(T):
    f = 1.0 + KAPPA * (1.0 - math.sqrt(T / TC))
    df = -KAPPA / (2.0 * math.sqrt(T * TC))
    d2f = KAPPA / (4.0 * T * math.sqrt(T * TC))
    return 0.45724 * R * R * TC * TC / PC * 2.0 * (df * df + f * d2f)


def _den(v):
    return v * v + 2.0 * B_PR * v - B_PR * B_PR


def pr_pressure(T, v):
    return R * T / (v - B_PR) - pr_a(T) / _den(v)


def dpdv(T, v):
    return -R * T / (v - B_PR) ** 2 + pr_a(T) * (2.0 * v + 2.0 * B_PR) / _den(v) ** 2


def dpdT_v(T, v):
    return R / (v - B_PR) - pr_da_dT(T) / _den(v)


def v_pr_roots(T, p):
    """Physical PR molar-volume roots (v > b) at (T, p), ascending."""
    A = pr_a(T) * p / (R * R * T * T)
    B = B_PR * p / (R * T)
    coeffs = (1.0, -(1.0 - B), A - 3.0 * B * B - 2.0 * B, -(A * B - B * B - B ** 3))
    out = []
    for Z in cubic_roots(*coeffs):
        v = Z * R * T / p
        if Z > B and v > B_PR and abs(pr_pressure(T, v) - p) <= 1e-6 * p:
            out.append(v)
    return sorted(out)


def v_pr(T, p):
    """PR molar volume: smallest physical root (liquid branch where three exist)."""
    roots = v_pr_roots(T, p)
    if not roots:
        raise ValueError("no physical PR root at T=%r p=%r" % (T, p))
    return roots[0]


def translation_at(T, vpr):
    """(v_m, c_m, dc_m, d_m) for a given PR molar volume, paper Eqs. (9)-(13)."""
    d = -(vpr * vpr / (R * TC)) * dpdv(T, vpr)
    c1 = 0.4266 * ZC_EXP - 0.1101
    c = (R * TC / PC) * (c1 - (0.004 + c1) * math.exp(-2.0 * d))
    dc = (R * TC / PC) * (ZC_EXP - ZC_PR)
    vm = vpr + c + dc * (0.35 / (0.35 + d))
    return vm, c, dc, d


def translation(T, p):
    """(v_m, v_PR, c_m, dc_m, d_m) implementing paper Eqs. (9)-(13)."""
    vpr = v_pr(T, p)
    vm, c, dc, d = translation_at(T, vpr)
    return vm, vpr, c, dc, d


def _log_term(v):
    return math.log((v + (1.0 - SQ2) * B_PR) / (v + (1.0 + SQ2) * B_PR))


def p_of_v_at(T, v):
    return pr_pressure(T, v)


def h_residual(T, v):
    """h(T,v) - h_ig(T), J/mol, PR departure function."""
    return (pr_a(T) - T * pr_da_dT(T)) / (2.0 * SQ2 * B_PR) * _log_term(v) + (p_of_v_at(T, v) * v - R * T)


def cv_residual(T, v):
    """c_v(T,v) - c_v_ig(T), J/(mol K), PR departure function.

    (dc_v/dv)_T = T (d2p/dT2)_v = -T a''/(v^2+2bv-b^2), integrated from v=inf.
    """
    return -T * pr_d2a_dT2(T) / (2.0 * SQ2 * B_PR) * _log_term(v)


def h_ideal_shomate(T):
    """Ideal-gas enthalpy of O2, J/mol, NIST Shomate (100-700 K), H(298.15)=0 ref."""
    A, B, C, D, E = SHOMATE
    F, H = -8.903471, 0.0
    t = T / 1000.0
    return 1000.0 * (A * t + B * t * t / 2.0 + C * t ** 3 / 3.0 + D * t ** 4 / 4.0 - E / t + F - H)


def cp_ideal_shomate(T):
    """Ideal-gas cp of O2, J/(mol K), NIST Shomate (100-700 K)."""
    A, B, C, D, E = SHOMATE
    t = T / 1000.0
    return A + B * t + C * t * t + D * t ** 3 + E / (t * t)


def cp_pr(T, p):
    """PR cp (J/(mol K)): c_p = c_v - T (dp/dT_v)^2/(dp/dv)_T on the PR volume."""
    v = v_pr(T, p)
    cv = cp_ideal_shomate(T) - R + cv_residual(T, v)
    return cv - T * dpdT_v(T, v) ** 2 / dpdv(T, v)


def cp_pr_fd(T, p, dT=1e-3):
    """Independent 4th-order central-difference check of cp_pr via h(T,p)."""
    def h(TT):
        return h_ideal_shomate(TT) + h_residual(TT, v_pr(TT, p))
    return (-h(T + 2 * dT) + 8.0 * h(T + dT) - 8.0 * h(T - dT) + h(T - 2 * dT)) / (12.0 * dT)


def state(T, p=P_FIG1):
    vm, vpr, c, dc, d = translation(T, p)
    return dict(T_K=T, p_Pa=p, rho_VTA=M_O2 / vm, rho_PR=M_O2 / vpr,
                v_VTA=vm, v_PR=vpr, c_m=c, dc_m=dc, d_m=d,
                Z_VTA=p * vm / (R * T), Z_PR=p * vpr / (R * T),
                cp_PR_J_molK=cp_pr(T, p), cp_PR_J_kgK=cp_pr(T, p) / M_O2,
                cp_ideal_J_kgK=cp_ideal_shomate(T) / M_O2,
                h_residual_J_mol=h_residual(T, vpr),
                n_roots=len(v_pr_roots(T, p)))
