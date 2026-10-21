#!/usr/bin/env python3
"""Self-checks for the pure-O2 PR / PR-VTA property model (stdlib unittest)."""

import math
import unittest

import oxygen_properties as op


class IdealLimit(unittest.TestCase):
    def test_low_pressure_limit(self):
        """At p -> 0 the model must approach the ideal gas: Z -> 1, cp -> cp_ig."""
        T, p = 300.0, 1.0e2
        s = op.state(T, p)
        self.assertAlmostEqual(s["Z_PR"], 1.0, delta=2.0e-4)
        self.assertAlmostEqual(s["rho_PR"], p * op.M_O2 / (op.R * T), delta=1e-3 * s["rho_PR"])
        self.assertAlmostEqual(s["cp_PR_J_molK"], op.cp_ideal_shomate(T), delta=2e-3)

    def test_ideal_limit_temperature_sweep(self):
        for T in (85.0, 150.0, 300.0):
            s = op.state(T, 1.0e2)
            self.assertLess(abs(s["Z_VTA"] - 1.0), 5e-4, msg="T=%r" % T)


class Derivatives(unittest.TestCase):
    def test_dpdv_analytic_vs_fd(self):
        for T in (85.0, 140.0, 157.5, 300.0):
            v = op.v_pr(T, op.P_FIG1)
            h = 1e-9 * v
            fd = (op.pr_pressure(T, v + h) - op.pr_pressure(T, v - h)) / (2 * h)
            self.assertAlmostEqual(op.dpdv(T, v) / fd, 1.0, delta=1e-6, msg="T=%r" % T)

    def test_dpdT_analytic_vs_fd(self):
        for T in (85.0, 140.0, 300.0):
            v = op.v_pr(T, op.P_FIG1)
            h = 1e-4
            fd = (op.pr_pressure(T + h, v) - op.pr_pressure(T - h, v)) / (2 * h)
            self.assertAlmostEqual(op.dpdT_v(T, v) / fd, 1.0, delta=1e-8, msg="T=%r" % T)

    def test_cp_analytic_vs_enthalpy_fd(self):
        """cp from the closed-form departure functions vs numerical dH/dT|p."""
        for T in (85.0, 100.0, 130.0, 155.0, 158.0, 200.0, 300.0):
            ana = op.cp_pr(T, op.P_FIG1)
            fd = op.cp_pr_fd(T, op.P_FIG1)
            self.assertAlmostEqual(ana / fd, 1.0, delta=1e-7, msg="T=%r" % T)

    def test_cv_residual_against_u_derivative(self):
        for T in (85.0, 160.0, 300.0):
            v = op.v_pr(T, op.P_FIG1)
            h = 1e-4

            def u_res(TT):
                return op.h_residual(TT, v) - (op.pr_pressure(TT, v) * v - op.R * TT)

            fd = (u_res(T + h) - u_res(T - h)) / (2 * h)
            self.assertAlmostEqual(op.cv_residual(T, v) / fd, 1.0, delta=1e-7, msg="T=%r" % T)


class Consistency(unittest.TestCase):
    def test_cubic_roots_are_pressure_roots(self):
        for T in (85.0, 150.0, 155.0, 157.5, 200.0, 300.0):
            roots = op.v_pr_roots(T, op.P_FIG1)
            self.assertTrue(1 <= len(roots) <= 3, msg="T=%r %r" % (T, roots))
            for v in roots:
                self.assertLess(abs(op.pr_pressure(T, v) - op.P_FIG1) / op.P_FIG1, 1e-9)

    def test_pr_critical_point(self):
        """The PR EoS evaluated at v_c = Zc_PR R Tc/pc must give pc and a flat
        isotherm. The published rounded constants (Omega_a = 0.45724,
        Omega_b = 0.07780) are mutually inconsistent at the 1e-5 level
        (3*Zc^2 + 3*B^2 + 2*B = 0.457229 != 0.45724), so p(v_c) is 8.6e-5 above
        pc and dp/dv does not vanish exactly (2.4e-4 relative). Both residuals
        are the rounding effect of the published constants, not a model error."""
        vc = op.ZC_PR * op.R * op.TC / op.PC
        self.assertAlmostEqual(op.pr_pressure(op.TC, vc) / op.PC, 1.0, delta=3e-4)
        self.assertAlmostEqual(op.dpdv(op.TC, vc) * vc / op.PC, 0.0, delta=1e-3)

    def test_translation_algebra_at_critical_point(self):
        """Eq. (9) at the critical point: d_m = 0, c_m = -0.004 RTc/pc, so the
        translated volume is (Zc_exp - 0.004) RTc/pc. This is the algebraic
        identity implied by Eqs. (9)-(13); it is the exact critical-point
        property of the formulation and is asserted symbolically (the numerical
        cubic root is ill-conditioned at a triple root)."""
        vc_pr = op.ZC_PR * op.R * op.TC / op.PC
        vm, c, dc, d = op.translation_at(op.TC, vc_pr)
        self.assertLess(abs(d), 2e-4)   # 7.3e-5 from rounded Omega_a/Omega_b
        self.assertAlmostEqual(c / (op.R * op.TC / op.PC), -0.004, delta=1e-5)
        self.assertAlmostEqual(vm / (op.R * op.TC / op.PC), op.ZC_EXP - 0.004, delta=1e-5)

    def test_density_monotone(self):
        prev = None
        T = 85.0
        while T <= 300.0 + 1e-9:
            rho = op.state(T)["rho_VTA"]
            if prev is not None:
                self.assertLess(rho, prev, msg="T=%r" % T)
            prev = rho
            T += 0.5

    def test_units(self):
        s = op.state(300.0, 1.0e2)
        # rho [kg/m3] = M [kg/mol] / v [m3/mol]; cp [J/kg/K] = cp [J/mol/K] / M
        self.assertAlmostEqual(s["rho_PR"] * s["v_PR"], op.M_O2, delta=1e-15)
        self.assertAlmostEqual(s["cp_PR_J_kgK"] * op.M_O2, s["cp_PR_J_molK"], delta=1e-9)


class LiteratureAnchors(unittest.TestCase):
    """Values read from Mueller & Pfitzner (2015) Fig. 1 and its text."""

    def test_vta_density_at_85K_matches_nist_marker(self):
        rho = op.state(85.0)["rho_VTA"]
        self.assertAlmostEqual(rho / 1177.2, 1.0, delta=1e-3)

    def test_pr_density_at_85K_matches_published_curve(self):
        rho = op.state(85.0)["rho_PR"]
        self.assertAlmostEqual(rho / 1328.52, 1.0, delta=1e-3)

    def test_pr_density_at_300K_matches_published_curve(self):
        """Published vector curve at 299.5 K is 75.29 kg/m3; the extraction
        resolution of the density panel is ~0.15 kg/m3 (0.2 %)."""
        rho = op.state(299.5)["rho_PR"]
        self.assertAlmostEqual(rho / 75.29, 1.0, delta=3e-3)

    def test_pr_cp_at_300K_matches_published_curve(self):
        cp = op.state(300.0)["cp_PR_J_kgK"]
        self.assertAlmostEqual(cp / 1019.28, 1.0, delta=2e-3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
