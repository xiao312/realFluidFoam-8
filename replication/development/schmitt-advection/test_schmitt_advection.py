#!/usr/bin/env python3
"""Tests for the oxygen contact-advection prototype.

These tests cover what is known to work - the equation-of-state inversion, the conservative
form of the update, and the sound speed - and they also pin the *reason* the prototype's
advection run is not yet usable, so that the limitation is a measured number in the repository
rather than a sentence in a report.
"""
import math
import unittest

import schmitt_advection as S


class EosInversion(unittest.TestCase):
    def test_density_to_temperature_round_trip(self):
        for rho in (1014.0, 900.0, 770.0, 600.0, 400.0, 200.0, 100.0):
            T = S.temperature_of_rho(rho)
            self.assertLess(abs(S.pressure_of(rho, T) - S.P_INITIAL), 1.0,
                            'rho=%g gives p=%g' % (rho, S.pressure_of(rho, T)))

    def test_energy_inversion_round_trip(self):
        for rho in (1000.0, 700.0, 400.0, 120.0):
            T = S.temperature_of_rho(rho)
            e = S.primitive_at(T, rho)['e']
            recovered = S.temperature_of_energy(rho, e, 300.0)
            self.assertLess(abs(recovered - T), 1e-6, 'rho=%g T=%g -> %g' % (rho, T, recovered))

    def test_endpoint_conditions_match_the_registered_target(self):
        # The registered conditions are rho 1000 -> 100 kg/m3 at about 6 MPa; the temperature
        # panel then follows from the equation of state rather than being imposed.
        self.assertAlmostEqual(S.temperature_of_rho(1000.0), 117.11, places=2)
        self.assertAlmostEqual(S.temperature_of_rho(100.0), 248.90, places=2)

    def test_sound_speed_is_finite_and_positive(self):
        for rho in (1000.0, 400.0, 100.0):
            T = S.temperature_of_rho(rho)
            c2 = S.primitive_at(T, rho)['c2']
            self.assertGreater(c2, 0.0)
            self.assertLess(c2, 1.0e7)

    def test_energy_below_the_admissible_floor_is_rejected(self):
        rho = 770.0
        lo, _ = S.temperature_window(rho)
        e_floor = S.primitive_at(lo, rho)['e']
        with self.assertRaises(ValueError):
            S.temperature_of_energy(rho, e_floor - 1.0e4, 300.0)


class ConservativeUpdate(unittest.TestCase):
    def test_uniform_state_is_unchanged(self):
        rho, T = 500.0, S.temperature_of_rho(500.0)
        q, props = S.conservative(rho, 10.0, T)
        flux = S.rusanov(q, q, props['p'], props['p'],
                         math.sqrt(props['c2']), math.sqrt(props['c2']))
        self.assertAlmostEqual(flux[0] - q[1], 0.0, places=9)
        self.assertAlmostEqual(flux[1] - (q[1] * 10.0 + props['p']), 0.0, places=3)
        self.assertAlmostEqual(flux[2] - 10.0 * (q[2] + props['p']), 0.0, places=3)

    def test_rusanov_dissipation_dominates_at_a_one_cell_interface(self):
        """The measured reason the first-order run is unusable.

        Across a single-cell 1000 -> 100 kg/m3 step, the Lax-Friedrichs dissipation on the
        total-energy component is about thirty times the physical advective energy flux. That
        is a property of the conserved formulation with an SRK internal-energy offset, not a
        coding slip: it is why the prototype records a blow-up (pressure 3-20 MPa, velocity
        -55 to +24 m/s, 46048 clamped cell-steps) at order 1 and never reaches a usable profile.
        A HLLC flux, whose dissipation is restricted to the star region, is the required fix.
        """
        rhoL, rhoR = S.RHO_DENSE, S.RHO_LIGHT
        qL, pL = S.conservative(rhoL, S.U_INITIAL, S.temperature_of_rho(rhoL))
        qR, pR = S.conservative(rhoR, S.U_INITIAL, S.temperature_of_rho(rhoR))
        a = max(abs(S.U_INITIAL) + math.sqrt(pL['c2']),
                abs(S.U_INITIAL) + math.sqrt(pR['c2']))
        physical = S.U_INITIAL * (qL[2] + pL['p'])
        dissipation = 0.5 * a * (qR[2] - qL[2])
        self.assertGreater(abs(dissipation / physical), 10.0)

    def test_observed_order_one_run_is_recorded_as_unusable(self):
        """The retained coarse run, so a later scheme can be compared against it."""
        import json
        import pathlib
        path = pathlib.Path(__file__).resolve().parent / 'runs' / 'order1-dx0.02' / 'run-dx-0.02.json'
        if not path.exists():
            self.skipTest('coarse order-1 run not present in this checkout')
        doc = json.loads(path.read_text())
        m = doc['metrics']
        self.assertGreater(m['clamped_cell_steps'], 1000)
        self.assertIsNone(m['interface_travel_m'])
        # The conservation certificate still holds exactly: the update is conservative even
        # when the states it produces are not admissible.
        for key in ('mass', 'momentum', 'energy'):
            self.assertLess(abs(m['conservation_residual_rel'][key]), 1e-12)


if __name__ == '__main__':
    unittest.main()
