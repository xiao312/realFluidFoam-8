#!/usr/bin/env python3
"""Tests for srk_chung.py: units, limits, thermodynamic consistency, provenance.

Every test either compares against an independent route (finite differences, a
pressure integral, a different transport correlation) or against the retained
mechanism file the constants were taken from.  None of them compares against the
published figure, so a failure here is a code or constants defect, not a scientific
disagreement.

Run: python3 test_srk_chung.py     (stdlib only, ~2 s)
"""
import math
import re
import unittest
from pathlib import Path

import srk_chung as sc

MECHANISM_REL = Path("replication/validation/inputs/property-thermo.inputData")


def find_mechanism():
    """Locate the retained mechanism file in the checkout or in the frozen snapshot.

    The scheduler job extracts an archive that holds this directory plus the mechanism
    file under the same repository-relative paths, so walking up from this file finds it
    in both layouts.  A missing file is a hard error: the provenance test must not pass
    by being skipped.
    """
    for base in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
        candidate = base / MECHANISM_REL
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "retained mechanism file not found next to this snapshot: " + str(MECHANISM_REL))


MECHANISM = find_mechanism()


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


class IdealGasAndProvenance(unittest.TestCase):
    def test_nasa7_and_critical_data_match_retained_mechanism(self):
        text = MECHANISM.read_text()
        for name in ("O2", "CH4"):
            block = text[text.index("\n" + name + "\n"):]
            block = block[:block.index("\n}\n")]
            low = [float(v) for v in re.search(
                r"lowCpCoeffs\s*\(([^)]*)\)", block).group(1).split()[:7]]
            high = [float(v) for v in re.search(
                r"highCpCoeffs\s*\(([^)]*)\)", block).group(1).split()[:7]]
            # the retained file stores 6 significant digits; the module keeps the
            # full GRI30 coefficients, so equality is to the file's precision
            with self.subTest(species=name, branch="low"):
                for got, want in zip(sc.SPECIES[name]["nasa7"][0], low):
                    self.assertLess(rel(got, want), 1e-5)
            with self.subTest(species=name, branch="high"):
                for got, want in zip(sc.SPECIES[name]["nasa7"][1], high):
                    self.assertLess(rel(got, want), 1e-5)

            mol_weight = float(re.search(r"molWeight\s+([0-9.]+)", block).group(1))
            self.assertAlmostEqual(sc.SPECIES[name]["molar_mass"] * 1e3, mol_weight,
                                   places=6)
            vc = float(re.search(r"\bVc\s+([0-9.]+)", block).group(1))
            self.assertAlmostEqual(sc.SPECIES[name]["vc"] * 1e6, vc, places=6)
            sigma = float(re.search(r"dataForKineticTrans\s*\{[^}]*?sigma\s+([0-9.]+)",
                                    block, re.S).group(1))
            self.assertAlmostEqual(sc.SPECIES[name]["lj_sigma"] * 1e10, sigma, places=6)

    def test_ideal_gas_limits(self):
        for name, species in sc.SPECIES.items():
            with self.subTest(species=name):
                T, p = 400.0, 1.0
                state = sc.thermo_state(species, T, p)
                ideal = p * species["molar_mass"] / (sc.R * T)
                self.assertLess(rel(state["rho"], ideal), 1e-6)
                self.assertLess(abs(state["h_dep"]) / sc.R / T, 1e-6)
                self.assertLess(abs(state["cp_dep"]) / sc.R, 1e-6)

    def test_critical_point_is_the_srk_solution(self):
        """At (Tc, pc) the cubic is a near-triple root and Z must solve the EOS.

        The published five-digit constants miss Zc = 1/3 exactly (the residual is
        O(1e-7) in the reduced cubic, amplified to O(1e-2) in Z because the critical
        root is degenerate), so the meaningful check is the equation of state itself
        plus a loose bracket on Zc.
        """
        for name, species in sc.SPECIES.items():
            with self.subTest(species=name):
                state = sc.srk_state(species, species["Tc"], species["pc"])
                v = state["v"]
                p_eos = (sc.R * state["T"] / (v - state["b"])
                         - state["a"] / (v * (v + state["b"])))
                self.assertLess(rel(p_eos, species["pc"]), 1e-12)
                self.assertLess(abs(state["Z"] - 1.0 / 3.0), 2e-2)


class ThermodynamicConsistency(unittest.TestCase):
    def test_departure_enthalpy_derivative_is_heat_capacity(self):
        for name, species in sc.SPECIES.items():
            for T in (100.0, 130.0, 145.0, 210.0, 250.0, 400.0):
                with self.subTest(species=name, T=T):
                    p = 56e5
                    step = 1e-3 * T
                    plus = sc.thermo_state(species, T + step, p)
                    minus = sc.thermo_state(species, T - step, p)
                    numeric = (plus["h"] - minus["h"]) / (2.0 * step)
                    state = sc.thermo_state(species, T, p)
                    self.assertLess(rel(numeric, state["cp"]), 2e-4)

    def test_departure_enthalpy_pressure_integral(self):
        """h_dep = integral_0^p [v - T (dv/dT)_p] dp, an independent route."""
        for name, species in sc.SPECIES.items():
            for T in (1.02 * species["Tc"], 250.0, 400.0):
                with self.subTest(species=name, T=T):
                    target_p = 56e5
                    steps = 4000
                    total = 0.0
                    for k in range(steps):
                        p = (k + 0.5) * target_p / steps
                        state = sc.srk_state(species, T, p)
                        total += (state["v"] - T * state["v_t"]) * target_p / steps
                    state = sc.srk_state(species, T, target_p)
                    self.assertLess(rel(total, state["h_dep"]), 2e-3)

    def test_cv_below_cp_and_positive(self):
        for name, species in sc.SPECIES.items():
            for T in (100.0, 154.58, 200.0, 400.0):
                with self.subTest(species=name, T=T):
                    state = sc.thermo_state(species, T, 56e5)
                    self.assertGreater(state["cv"], 0.0)
                    self.assertLess(state["cv"], state["cp"])
                    self.assertGreater(state["cv"], sc.R * 1.4)

    def test_single_phase_above_critical_pressure(self):
        """At 56 bar (above both pc) the sweep must not hop branches."""
        for name, species in sc.SPECIES.items():
            with self.subTest(species=name):
                self.assertGreater(56e5, species["pc"])
                previous = None
                for k in range(100, 401):
                    state = sc.srk_state(species, float(k), 56e5)
                    self.assertEqual(state["n_stable_roots"], 1,
                                     "unexpected root multiplicity at T=%g" % k)
                    if previous is not None:
                        self.assertGreater(state["rho"], 0.0)
                    previous = state["rho"]


class Transport(unittest.TestCase):
    def test_dilute_limit_is_the_chapman_enskog_term(self):
        for name, species in sc.SPECIES.items():
            for T in (150.0, 300.0, 400.0):
                with self.subTest(species=name, T=T):
                    dilute = sc.chung_dilute(species, T)
                    state = sc.chung_state(species, T, 101325.0, rho=1e-6,
                                          cp_ideal_value=sc.cp_ideal(species, T))
                    self.assertLess(rel(state["mu"], 0.1 * dilute["eta0"]), 1e-6)
                    self.assertAlmostEqual(state["g2"], 1.0, places=6)

    def test_dilute_viscosity_matches_kinetic_theory(self):
        for name, species in sc.SPECIES.items():
            for T in (300.0, 400.0):
                with self.subTest(species=name, T=T):
                    chung = 0.1 * sc.chung_dilute(species, T)["eta0"]
                    kinetic = sc.kinetic_viscosity(species, T)
                    self.assertLess(rel(chung, kinetic), 0.08,
                                    "Chung %g vs kinetic %g" % (chung, kinetic))

    def test_dilute_conductivity_matches_modified_eucken(self):
        for name, species in sc.SPECIES.items():
            for T in (250.0, 400.0):
                with self.subTest(species=name, T=T):
                    mu = 0.1 * sc.chung_dilute(species, T)["eta0"]
                    eucken = sc.eucken_conductivity(species, T, mu)
                    state = sc.chung_state(species, T, 101325.0, rho=1e-6)
                    self.assertLess(rel(state["kappa"], eucken), 0.12,
                                    "Chung %g vs Eucken %g" % (state["kappa"], eucken))

    def test_conductivity_prefactor_is_the_thermochemical_calorie(self):
        """kappa carries one calorie definition, and the printed one is 6.694e-04 away.

        Round 4 found `kappa_cond` multiplying by 418.6798 (International-Table
        calorie) while `cv_cal` used 1/4.184.  The factor is now derived from
        CAL_PER_JOULE, and this test pins both the derivation and the size of the
        offset the old constant carried, so a future edit cannot quietly reintroduce
        a second definition.
        """
        self.assertAlmostEqual(sc.CAL_CM_S_K_TO_W_M, 100.0 / sc.CAL_PER_JOULE, places=12)
        self.assertAlmostEqual(sc.CAL_CM_S_K_TO_W_M, 418.4, places=12)
        offset = sc.CAL_CM_S_K_TO_W_M_INTERNATIONAL / sc.CAL_CM_S_K_TO_W_M - 1.0
        self.assertLess(rel(offset, 6.694e-04), 1e-3,
                        "the two calorie definitions differ by %g" % offset)
        # kappa is the prefactor times the raw cal/(cm s K) correlation value, so the
        # prefactor cannot enter anywhere else without breaking this identity.
        state = sc.chung_state(sc.SPECIES["O2"], 300.0, 56e5)
        raw = state["lambda_k"] + state["lambda_p"]
        self.assertLess(rel(state["kappa"], raw * sc.CAL_CM_S_K_TO_W_M), 1e-14)

    def test_conductivity_is_pinned_for_one_state(self):
        """One hand-computed state, with its terms, so the constants cannot drift.

        O2 at 300 K and 56 bar.  alpha (Eq. 9) = 1.0345725252670, psi (Eq. 11) =
        1.33240503514327, h2 (Eq. 12) = 0.860081029887503, lambda0 = 6.376939233246657e-05
        cal/(cm s K), lambda_k = 6.411073456498698e-05, lambda_p = 3.0351272733410096e-06,
        kappa = 418.4 * (lambda_k + lambda_p) = 0.028093828593156435 W/(m K).
        """
        state = sc.chung_state(sc.SPECIES["O2"], 300.0, 56e5)
        self.assertLess(rel(state["alpha_eucken"], 1.0345725252670004), 1e-12)
        self.assertLess(rel(state["psi"], 1.332405035143271), 1e-12)
        self.assertLess(rel(state["h2"], 0.8600810298875033), 1e-12)
        self.assertLess(rel(state["lambda0"], 6.376939233246657e-05), 1e-12)
        self.assertLess(rel(state["kappa"], 0.028093828593156435), 1e-12)
        self.assertLess(rel(state["mu"], 2.1382480546358256e-05), 1e-12)

    def test_dense_correction_increases_viscosity(self):
        for name, species in sc.SPECIES.items():
            with self.subTest(species=name):
                T, p = 200.0, 56e5
                dense = sc.chung_state(species, T, p)
                dilute = 0.1 * sc.chung_dilute(species, T)["eta0"]
                self.assertGreater(dense["mu"], dilute)
                self.assertGreater(dense["kappa"], 0.0)
                self.assertLess(dense["y"], 1.0)


class SweepSanity(unittest.TestCase):
    def test_density_and_transport_ranges_at_56_bar(self):
        """Coarse physical ranges; the figure comparison is the real check."""
        bounds = {
            "O2": {"rho": (40.0, 1300.0), "cp": (20.0, 260.0),
                   "mu": (1.0e-5, 3.0e-4), "kappa": (0.01, 0.50)},
            "CH4": {"rho": (20.0, 600.0), "cp": (30.0, 260.0),
                    "mu": (1.0e-5, 3.0e-4), "kappa": (0.01, 0.50)},
        }
        for name, species in sc.SPECIES.items():
            for T in (100.0, 200.0, 300.0, 400.0):
                with self.subTest(species=name, T=T):
                    state = sc.thermo_state(species, T, 56e5)
                    transport = sc.chung_state(species, T, 56e5,
                                               rho=state["rho"],
                                               cp_ideal_value=state["cp_ideal"])
                    lo, hi = bounds[name]["rho"]
                    self.assertTrue(lo <= state["rho"] <= hi,
                                    "rho=%g at %g K" % (state["rho"], T))
                    lo, hi = bounds[name]["cp"]
                    self.assertTrue(lo <= state["cp"] <= hi,
                                    "cp=%g at %g K" % (state["cp"], T))
                    lo, hi = bounds[name]["mu"]
                    self.assertTrue(lo <= transport["mu"] <= hi,
                                    "mu=%g at %g K" % (transport["mu"], T))
                    lo, hi = bounds[name]["kappa"]
                    self.assertTrue(lo <= transport["kappa"] <= hi,
                                    "kappa=%g at %g K" % (transport["kappa"], T))


if __name__ == "__main__":
    unittest.main(verbosity=2)
