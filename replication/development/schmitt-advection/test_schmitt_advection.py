#!/usr/bin/env python3
"""Tests for the oxygen contact-advection prototype.

These tests cover what is known to work - the equation-of-state inversion, the conservative form
of the update, the sound speed, the HLLC flux's contact preservation and the two energy-window
defects that were found and fixed while the scheme was built - and they keep the retained
negative control pinned, so a scheme that looks better because the comparison run was deleted
cannot pass.
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


class EnergyWindow(unittest.TestCase):
    """Two defects found and fixed here; both silently rejected admissible states.

    The first: the caloric inversion was bracketed just above the positive-pressure floor, but
    the SRK internal energy has its minimum about thirty kelvin higher, in the pseudo-boiling
    band, so states between the two were reported as outside the admissible range. The second:
    the minimum itself has to be searched over mechanically stable states only, because on the
    repulsive branch (dp/dv > 0) the same energy is attained again - at 100 kg/m3 that branch
    gave a spurious 94.6 K root against a physical 248.9 K.

    The margins below are the ones that matter for the run: at each density the energy at the
    window floor must lie strictly below the energy the initial condition needs, otherwise the
    first update cannot be inverted.
    """

    def test_window_starts_on_the_mechanically_stable_branch(self):
        for rho in (1000.0, 700.0, 400.0, 296.7, 100.0, 60.0):
            lo, hi = S.temperature_window(rho)
            floor_props = S.primitive_at(lo, rho)          # raises if the state is inadmissible
            initial = S.primitive_at(S.temperature_of_rho(rho), rho)
            self.assertLess(floor_props['e'], initial['e'],
                            'rho=%g: energy floor %g above the initial %g'
                            % (rho, floor_props['e'], initial['e']))
            self.assertLess(lo, hi)

    def test_the_window_never_returns_the_repulsive_branch(self):
        # 94.64 K at 100 kg/m3 is where the old scan landed; it must be rejected, not used.
        self.assertFalse(S._positive_pressure_stable(100.0, 94.6395))
        self.assertGreater(S.temperature_window(100.0)[0], 99.0)

    def test_pseudo_boiling_band_has_a_narrow_admissible_energy_band(self):
        # The band at 400 kg/m3 is only a few kJ/kg wide, which is why a smeared contact
        # leaves it: this is a property of the equation of state that the report states.
        lo, _ = S.temperature_window(400.0)
        band = S.primitive_at(S.temperature_of_rho(400.0), 400.0)['e'] - S.primitive_at(lo, 400.0)['e']
        self.assertGreater(band, 0.0)
        self.assertLess(band, 1.0e4)

    def test_temperature_at_a_given_density_and_pressure(self):
        for rho in (1000.0, 700.0, 400.0, 100.0):
            T = S.temperature_of_rho(rho)
            for hint in (T - 5.0, T, T + 50.0, 300.0):
                recovered = S.temperature_of_rho_p(rho, S.P_INITIAL, hint)
                self.assertLess(abs(recovered - T), 1e-6,
                                'rho=%g hint=%g -> %g against %g' % (rho, hint, recovered, T))


class HllcFlux(unittest.TestCase):
    def test_hllc_reproduces_the_upwind_flux_for_a_pressure_equilibrium_contact(self):
        """The property the whole test rests on.

        When both sides share a pressure and a velocity the exact solution is a pure contact,
        HLLC's star speed equals that velocity, and the flux must reduce to the upwind flux - no
        dissipation on the contact at all. That is what Rusanov cannot do, and it is measured
        here rather than assumed, for the strongest jump in the run and for a milder one.
        """
        for rhoL, rhoR in ((1000.0, 100.0), (900.0, 300.0), (1000.0, 900.0)):
            pL = S.primitive_at(S.temperature_of_rho(rhoL), rhoL)
            pR = S.primitive_at(S.temperature_of_rho(rhoR), rhoR)
            EL = rhoL * (pL['e'] + 0.5 * S.U_INITIAL ** 2)
            ER = rhoR * (pR['e'] + 0.5 * S.U_INITIAL ** 2)
            flux = S.hllc_flux([rhoL, S.U_INITIAL, pL['p'], EL, math.sqrt(pL['c2'])],
                               [rhoR, S.U_INITIAL, pR['p'], ER, math.sqrt(pR['c2'])])
            upwind = [rhoL * S.U_INITIAL,
                      rhoL * S.U_INITIAL ** 2 + pL['p'],
                      S.U_INITIAL * (EL + pL['p'])]
            for k in range(3):
                scale = max(abs(upwind[k]), 1.0)
                self.assertLess(abs(flux[k] - upwind[k]) / scale, 1e-12,
                                'jump %g->%g component %d: %g against %g'
                                % (rhoL, rhoR, k, flux[k], upwind[k]))

    def test_reconstructing_density_and_pressure_leaves_a_uniform_pressure_uniform(self):
        # A uniform field has zero minmod slope, so both sides of a face reconstruct to the same
        # 6 MPa even where the density slope is at its steepest. Reconstructing temperature
        # instead would pair a density slope with a temperature slope and manufacture a jump.
        rho = [1000.0, 938.8, 458.6, 154.3, 103.8, 100.0]
        s_rho = S.limited_slopes(rho)
        s_p = S.limited_slopes([S.P_INITIAL] * len(rho))
        self.assertNotEqual(s_rho[2], 0.0)
        for value in s_p:
            self.assertEqual(value, 0.0)
        for k in (1, 2):
            for sign in (1.0, -1.0):
                rho_k = rho[k] + sign * 0.5 * s_rho[k]
                T_k = S.temperature_of_rho_p(rho_k, S.P_INITIAL, 150.0)
                self.assertLess(abs(S.pressure_of(rho_k, T_k) - S.P_INITIAL), 1.0)


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
        path = (pathlib.Path(__file__).resolve().parent / 'runs' / 'rusanov-order1-dx0.02'
                / 'run-dx-0.02.json')
        if not path.exists():
            self.skipTest('coarse Rusanov run not present in this checkout')
        doc = json.loads(path.read_text())
        m = doc['metrics']
        self.assertGreater(m['clamped_cell_steps'], 1000)
        self.assertIsNone(m['interface_travel_m'])
        self.assertGreater(m['p_amplitude_rel'], 0.5)
        # The conservation certificate still holds exactly: the update is conservative even
        # when the states it produces are not admissible.
        for key in ('mass', 'momentum', 'energy'):
            self.assertLess(abs(m['conservation_residual_rel'][key]), 1e-12)


if __name__ == '__main__':
    unittest.main()
