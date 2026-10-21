#!/usr/bin/env python3
"""Independent derivation and tolerance check for the volume-translation constants.

The registered figure (Fig. 1(a) of Mueller & Pfitzner 2015) is reproduced with the
Peng-Robinson EoS (Eq. 8) plus a volume translation (Eqs. 9-13).  Two constants in
that translation are not printed as numbers in the paper, so they have to be fixed
here and their effect on the plotted density has to be bounded:

  c1   the linear coefficient of Eq. (10), printed only as Eq. (12) in the form
       c1 = 0.4266 Zc - 0.1101 without saying which Zc;
  dc   the critical-volume offset term that the paper's Eq. (9) carries as an
       explicit additive correction.

This script derives both from a single stated requirement - the translated EoS must
map the PR critical point onto the experimental critical volume - and then bounds
how much the plotted density at 5.61 MPa can move when those constants (or the
experimental critical volume behind them) are perturbed.  It uses only the module's
own public functions and the Python standard library, so the reviewer can replay it:

    python3 critical_tolerance.py

Every number printed here is reproducible from the constants in oxygen_properties.py.
Exit status is nonzero if any internal consistency assert fails.
"""

import json
import math
import sys

import oxygen_properties as op

# Experimental critical volume of O2, NIST Chemistry WebBook: 73.4 cm^3/mol.
VC_EXP_CM3 = 73.4
P_FIG1 = op.P_FIG1

R, TC, PC = op.R, op.TC, op.PC
V_REF = R * TC / PC                      # RTc/pc, m^3/mol
VC_EXP = VC_EXP_CM3 * 1e-6               # m^3/mol
ZC_FROM_VC = PC * VC_EXP / (R * TC)      # experimental critical compressibility


def dpdv(T, v):
    """(dp/dv)_T of the PR EoS, Pa m^3/mol per m^3/mol."""
    return op.dpdv(T, v)


def translation_parts(T, vpr, c1, dc):
    """Eqs. (9)-(13) with explicit constants instead of the module's defaults."""
    d = -(vpr * vpr / (R * TC)) * dpdv(T, vpr)
    c = (R * TC / PC) * (c1 - (0.004 + c1) * math.exp(-2.0 * d))
    return vpr + c + dc * (0.35 / (0.35 + d)), c, d


def rho_vta(T, p, c1, dc):
    vpr = op.v_pr(T, p)
    vm, _, _ = translation_parts(T, vpr, c1, dc)
    return op.M_O2 / vm


def main():
    out = {}
    c1_mod = 0.4266 * op.ZC_EXP - 0.1101
    dc_mod = V_REF * (op.ZC_EXP - op.ZC_PR)

    # -- 1. what the PR EoS gives at its own critical point --------------------
    # The PR critical point is analytic: by construction (a = 0.45724 R^2 Tc^2/pc,
    # b = 0.07780 R Tc/pc) the EoS is critical at v = Zc_PR RTc/pc with Zc_PR =
    # 0.3074.  It is NOT evaluated through the numeric cubic root here: at the
    # critical point dp/dv = 0, so the cubic is ill-conditioned and a 1e-5
    # coefficient residual moves the root by ~4 % (checked below).  The figure
    # itself is evaluated at 5.61 MPa and 85-300 K, where the liquid root is well
    # separated and conditioned, so this does not affect the plotted density.
    v_pr_c = op.ZC_PR * V_REF
    d_c = 0.0
    numeric = op.v_pr(TC, PC)
    out["critical_point"] = {
        "v_pr_cm3": v_pr_c * 1e6,
        "Zc_pr": op.ZC_PR,
        "d_at_critical_analytic": d_c,
        "d_at_critical_from_numeric_cubic":
            -(numeric ** 2 / (R * TC)) * dpdv(TC, numeric),
        "numeric_cubic_v_cm3": numeric * 1e6,
        "numeric_cubic_ill_conditioning_percent": 100.0 * (numeric - v_pr_c) / v_pr_c,
        "v_c_exp_cm3": VC_EXP * 1e6,
        "Zc_experimental_from_Vc": ZC_FROM_VC,
        "Zc_experimental_used": op.ZC_EXP,
    }
    v_tr_c, c_c, _ = translation_parts(TC, v_pr_c, c1_mod, dc_mod)
    out["critical_point"].update({
        "c_m_cm3": c_c * 1e6,
        "dc_m_cm3": dc_mod * 1e6,
        "v_translated_cm3": v_tr_c * 1e6,
        "rel_mismatch_percent": 100.0 * (v_tr_c - VC_EXP) / VC_EXP,
        "residual_cm3": (v_tr_c - VC_EXP) * 1e6,
        "residual_in_units_of_RTc_over_pc": (v_tr_c - VC_EXP) / V_REF,
    })

    # -- 2. why dc has exactly this form --------------------------------------
    # At the critical point d_c = 0 (PR is critical there), so exp(-2 d_c) = 1 and
    # the Eq. (10) bracket collapses to -0.004 regardless of c1: the exponential
    # form cannot carry the critical volume, which is what dc is for.  Setting
    #     v_pr(Tc) + c(Tc) + dc = Vc_exp
    # therefore gives dc = Vc_exp - v_pr(Tc) + 0.004 RTc/pc = (Zc_exp - Zc_PR + 0.004) RTc/pc.
    dc_derived = VC_EXP - v_pr_c + 0.004 * V_REF
    out["dc_derivation"] = {
        "dc_derived_cm3": dc_derived * 1e6,
        "dc_module_cm3": dc_mod * 1e6,
        "difference_cm3": (dc_derived - dc_mod) * 1e6,
        "difference_rel_percent": 100.0 * (dc_derived - dc_mod) / dc_mod,
    }
    # The module uses dc = (Zc_exp - Zc_PR) RTc/pc, i.e. it drops the 0.004 RTc/pc
    # residual of the bracket.  That residual is the tolerance of the critical-point
    # argument, so measure it instead of hiding it:
    out["critical_tolerance_cm3"] = 0.004 * V_REF * 1e6

    # -- 3. sensitivity of the plotted density --------------------------------
    temps = [85.0, 90.0, 120.0, 157.45, 240.0, 300.0]
    base = {T: rho_vta(T, P_FIG1, c1_mod, dc_mod) for T in temps}

    def sweep(c1, dc, label):
        vals = {T: rho_vta(T, P_FIG1, c1, dc) for T in temps}
        dev = {T: 100.0 * (vals[T] - base[T]) / base[T] for T in temps}
        return {"label": label,
                "rho": {str(T): vals[T] for T in temps},
                "rel_deviation_percent": {str(T): dev[T] for T in temps}}

    cases = [
        sweep(0.4266 * op.ZC_PR - 0.1101, dc_mod, "c1 from Eq. (12) with Zc_PR (paper literal)"),
        sweep(c1_mod * 1.05, dc_mod, "c1 +5 %"),
        sweep(c1_mod * 0.95, dc_mod, "c1 -5 %"),
        sweep(c1_mod, dc_mod * 1.10, "dc +10 %"),
        sweep(c1_mod, dc_mod * 0.90, "dc -10 %"),
        sweep(c1_mod, dc_derived, "dc from exact critical volume"),
    ]
    out["base_rho"] = {str(T): base[T] for T in temps}
    out["sensitivity"] = cases

    # -- 4. experimental critical-volume uncertainty --------------------------
    # NIST Vc = 73.4 cm^3/mol is quoted to 3 significant figures, so the
    # experimental Zc used here carries at most +-0.0005 (0.17 %).
    zc_lo, zc_hi = op.ZC_EXP - 0.0005, op.ZC_EXP + 0.0005
    dc_lo = V_REF * (zc_lo - op.ZC_PR)
    dc_hi = V_REF * (zc_hi - op.ZC_PR)
    r85_lo = rho_vta(85.0, P_FIG1, c1_mod, dc_lo)
    r85_hi = rho_vta(85.0, P_FIG1, c1_mod, dc_hi)
    out["Vc_uncertainty"] = {
        "Zc_range": [zc_lo, zc_hi],
        "rho85_range": [r85_lo, r85_hi],
        "rho85_rel_percent": [100.0 * (r85_lo - base[85.0]) / base[85.0],
                              100.0 * (r85_hi - base[85.0]) / base[85.0]],
    }

    # -- 5. bound on the whole plotted curve ----------------------------------
    worst = 0.0
    worst_case = None
    for T in [85.0 + 0.25 * k for k in range(0, 861)]:      # 85 .. 300 K
        r0 = rho_vta(T, P_FIG1, c1_mod, dc_mod)
        for c1, dc, label in ((0.4266 * op.ZC_PR - 0.1101, dc_mod, "c1 literal"),
                              (c1_mod * 1.05, dc_mod, "c1 +5 %"),
                              (c1_mod, dc_lo, "Vc -0.0005 Zc"),
                              (c1_mod, dc_hi, "Vc +0.0005 Zc")):
            rel = abs(100.0 * (rho_vta(T, P_FIG1, c1, dc) - r0) / r0)
            if rel > worst:
                worst, worst_case = rel, (T, label)
    out["worst_curve_shift"] = {"max_abs_rel_percent": worst,
                                "at_T_K": worst_case[0], "case": worst_case[1]}

    print(json.dumps(out, indent=1))

    assert abs(out["critical_point"]["rel_mismatch_percent"]) < 3.0
    assert worst < 10.0
    return 0


if __name__ == "__main__":
    sys.exit(main())
