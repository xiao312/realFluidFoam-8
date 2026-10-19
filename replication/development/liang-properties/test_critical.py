"""Check independent critical math at the pure-fluid and mixture boundaries."""
import unittest

import numpy as np

from critical_math import analytical, coefficients, composition, numerical_inflection


SPECIES = {
    "H2": dict(Tc=33.18, Pc=1.3e6, omega=-.216, molWeight=2.01594, Vc=64.935),
    "CH4": dict(Tc=190.6, Pc=4.61e6, omega=.011, molWeight=16.043, Vc=98.6),
    "O2": dict(Tc=154.58, Pc=5.043e6, omega=.025, molWeight=31.9988, Vc=73.529),
    "N2": dict(Tc=126.19, Pc=3.398e6, omega=.039, molWeight=28.0134, Vc=89.445),
}


class CriticalChecks(unittest.TestCase):
    def test_pure_fluid_recovery(self):
        # Allow truncation in the fork's .42747 and .08664 coefficients.
        for fuel, index, name in (("H2", 0, "H2"), ("CH4", 0, "CH4"),
                                  ("H2", 1, "O2"), ("H2", 2, "N2")):
            x = np.zeros(3)
            x[index] = 1
            result = analytical(coefficients(SPECIES, fuel, x))
            self.assertLess(abs(result["Tc_K"] / SPECIES[name]["Tc"] - 1), 1e-4)
            self.assertLess(abs(result["Pc_atm"] * 101325 / SPECIES[name]["Pc"] - 1), 1e-4)

    def test_pressure_inflection_independent_of_closed_form(self):
        for fuel in ("H2", "CH4"):
            model = coefficients(SPECIES, fuel, composition(fuel, 1))
            exact = analytical(model)
            numeric = numerical_inflection(model)
            self.assertLess(abs(exact["Tc_K"] - numeric["Tc_K"]), 2e-5)
            self.assertLess(abs(exact["Pc_atm"] - numeric["Pc_atm"]), 2e-5)

    def test_paper_hydrogen_implied_volume_exceeds_any_composition(self):
        # Regression for the observed mismatch: never silently accept this pair
        # as the fixed-composition critical point for these pure-species inputs.
        from critical_math import OMEGA_B, R
        implied = OMEGA_B * R * 98.11730677526087 / (21.11362914196203 * 101325)
        maximum = max(coefficients(SPECIES, "H2", composition("H2", 1))["bi"])
        self.assertGreater(implied, maximum * 1.2)

    def test_invalid_mole_fractions_fail(self):
        for x in (np.array([1., 1., 1.]), np.array([-1., 1., 1.]), np.array([np.nan, 0., 1.])):
            with self.assertRaises(ValueError):
                coefficients(SPECIES, "H2", x)


if __name__ == "__main__":
    unittest.main()
