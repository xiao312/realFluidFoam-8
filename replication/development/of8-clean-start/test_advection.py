"""Tests for the OF8 contact-advection case generator and its metrics.

These pin the properties that make the case a test rather than an illustration: the
interface width really is n_x * dx, the boundary is really periodic in x, the case really
starts at time 0 and reaches t = 20 ms, and the metric recovers the exact answer on a
synthetic state that is a pure shift of the initial condition.

Run: python3 -B -m unittest test_advection -v
"""
import json
import math
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import advection_metrics
import prepare_advection_case as gen


class InterfaceProfile(unittest.TestCase):

    def test_width_is_interface_cells_times_dx(self):
        for variant, cells in (('nx2', 2), ('nx4', 4), ('nx6', 6)):
            values, width = gen.temperature_profile(gen.VARIANTS[variant]['interface_cells'])
            self.assertAlmostEqual(width, cells * gen.DX)
            self.assertEqual(len(values), gen.CELLS)

    def test_profile_is_monotone_and_bounded(self):
        values, _ = gen.temperature_profile(6)
        # the widest interface (n_x = 6, width 0.06 m) still leaves the first cell within
        # a few kelvin of the cold state and the last cell within a few of the hot one
        self.assertLess(values[0], 302.0)
        self.assertGreater(values[-1], 2998.0)
        for a, b in zip(values, values[1:]):
            self.assertGreaterEqual(b, a)
        for v in values:
            self.assertGreaterEqual(v, gen.T_COLD)
            self.assertLessEqual(v, gen.T_HOT)

    def test_wider_interface_smooths_the_gradient(self):
        narrow, _ = gen.temperature_profile(2)
        wide, _ = gen.temperature_profile(6)
        gradient_narrow = max(b - a for a, b in zip(narrow, narrow[1:]))
        gradient_wide = max(b - a for a, b in zip(wide, wide[1:]))
        self.assertGreater(gradient_narrow, gradient_wide)

    def test_interface_sits_at_the_registered_position(self):
        """A sharp contact at x = 0.15 m in a 0.6 m domain leaves about a quarter cold.

        The 20 ms travel of 0.2 m then keeps the contact inside the periodic domain, which
        is what makes the shift comparison meaningful.
        """
        values, _ = gen.temperature_profile(2)
        hot = [v for v in values if v > 2500.0]
        cold = [v for v in values if v < 400.0]
        transition = len(values) - len(hot) - len(cold)
        self.assertTrue(3 <= transition <= 8, transition)
        self.assertTrue(10 <= len(cold) <= 18, len(cold))
        self.assertGreater(len(hot), 40)
        travel = gen.VELOCITY * gen.END_TIME
        self.assertLess(gen.INTERFACE_X + travel, gen.LENGTH)
        self.assertGreater(gen.INTERFACE_X - travel, -gen.LENGTH)


class Dictionaries(unittest.TestCase):

    def test_boundary_is_cyclic_in_x_only(self):
        text = gen.block_mesh()
        self.assertIn('left  { type cyclic; neighbourPatch right; faces ((0 4 7 3)); }', text)
        self.assertIn('right { type cyclic; neighbourPatch left; faces ((1 2 6 5)); }', text)
        self.assertIn('sides { type empty;', text)

    def test_controls_reach_twenty_milliseconds_from_time_zero(self):
        text = gen.control_dict()
        self.assertIn('startFrom       startTime;', text)
        self.assertRegex(text, r'endTime\s+0\.02;')
        self.assertIn('adjustTimeStep  yes;', text)
        self.assertRegex(text, r'maxCo\s+0\.4;')
        self.assertEqual(int(round(gen.END_TIME / gen.WRITE_INTERVAL)), 4)


class GeneratedCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='adv-case-'))
        self.source = Path('/workspace/forge-out/runs/of8-case-v1/case/constant')
        self.have_source = (self.source / 'thermo.inputData_GRI').exists()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_receipt_declares_mesh_state_and_limits(self):
        if not self.have_source:
            self.skipTest('frozen mechanism source not present')
        out = self.tmp / 'nx2'
        gen.write_case(out, 'nx2', self.source, 'deadbeef')
        receipt = json.loads(Path(str(out) + '.receipt.json').read_text())
        self.assertEqual(receipt['target'], 'schmitt2020-fig-5')
        self.assertEqual(receipt['mesh']['cells'], 60)
        self.assertAlmostEqual(receipt['mesh']['dx'], 0.01)
        self.assertEqual(receipt['initial_state']['interface_cells'], 2)
        self.assertAlmostEqual(receipt['initial_state']['interface_width_m'], 0.02)
        self.assertEqual(receipt['initial_state']['density_ratio_ideal_gas'], 10.0)
        self.assertEqual(receipt['chemistry'], 'off')
        self.assertEqual(receipt['controls']['expected_writes'], 4)
        self.assertIn('no real-fluid equation of state', receipt['scope'])
        self.assertEqual(receipt['file_count'], len(receipt['files']))

    def test_temperature_field_carries_temperature_dimensions(self):
        if not self.have_source:
            self.skipTest('frozen mechanism source not present')
        out = self.tmp / 'nx4'
        gen.write_case(out, 'nx4', self.source, 'deadbeef')
        text = (out / '0/T').read_text()
        self.assertIn('dimensions      [0 0 0 1 0 0 0];', text)
        self.assertIn('type cyclic', text)
        values = [float(v) for v in
                  re.search(r'nonuniform List<scalar>\s+60\s*\((.*?)\)\s*;', text, re.S)[1].split()]
        self.assertEqual(len(values), 60)
        self.assertLess(values[0], 300.1)

    def test_metric_recovers_the_exact_shift(self):
        if not self.have_source:
            self.skipTest('frozen mechanism source not present')
        out = self.tmp / 'nx2'
        gen.write_case(out, 'nx2', self.source, 'deadbeef')
        metrics = _make_synthetic_write(out, 0.002)
        self.assertEqual(metrics['times'][0]['time'], '0.002')
        row = metrics['times'][0]
        self.assertLess(abs(row['mass_rel_drift']), 1e-12)
        self.assertLess(abs(row['momentum_rel_drift']), 1e-12)
        self.assertLess(abs(row['energy_rel_drift']), 1e-12)
        self.assertLess(row['temperature_l2_error_K'], 1e-6)
        self.assertLess(row['pressure_deviation_rel'], 1e-15)
        self.assertLess(row['velocity_deviation_m_per_s'], 1e-15)
        self.assertEqual(row['cells'], 60)


def _make_synthetic_write(case, time):
    """Write a time directory that is a pure rigid shift of the initial state.

    The state is generated from the case's own initial fields and the JANAF/ideal-gas
    relations, so a metric that disagrees with the exact shift is wrong. This is a parser
    and algebra test, not a solver result.
    """
    from metrics import (R_UNIVERSAL, janaf_cp_over_R, read_scalar, species_table,
                         sensible_enthalpy_MJ)

    names, table = species_table((case / 'constant/thermo.inputData_GRI').read_text())
    n = gen.CELLS
    dx = gen.DX
    t0 = read_scalar(case / '0/T', n)
    p0 = gen.PRESSURE
    shifted = []
    for i in range(n):
        x = (i + 0.5) * dx - gen.VELOCITY * time
        position = (x % (n * dx)) / dx - 0.5
        i0 = int(math.floor(position))
        fraction = position - i0
        i0 %= n
        i1 = (i0 + 1) % n
        shifted.append((1.0 - fraction) * t0[i0] + fraction * t0[i1])
    composition = {'O2': 0.23, 'N2': 0.77}
    ys = {s: [composition.get(s, 0.0)] * n for s in names}
    molar = [1.0 / sum(ys[s][i] / table[s]['weight'] for s in names) for i in range(n)]
    rho = [p0 * molar[i] / (R_UNIVERSAL * shifted[i]) for i in range(n)]
    cp = []
    for i in range(n):
        cp.append(sum(ys[s][i] * R_UNIVERSAL / table[s]['weight']
                      * janaf_cp_over_R(table[s]['coeffs'][
                          'low' if shifted[i] <= table[s]['tcommon'] else 'high'], shifted[i])
                      for s in names))
    directory = case / time.__repr__().rstrip('0').rstrip('.')
    if not directory.exists():
        directory = case / ('%g' % time)
    directory.mkdir(parents=True, exist_ok=True)

    def write_scalar(name, values, dims='[0 0 0 0 0 0 0]'):
        body = '\n'.join(repr(float(v)) for v in values)
        (directory / name).write_text(
            'FoamFile\n{\n    version 2.0;\n    format ascii;\n    class volScalarField;\n'
            '    object %s;\n}\n\ndimensions %s;\n'
            'internalField nonuniform List<scalar>\n%d\n(\n%s\n)\n;\n'
            'boundaryField\n{\n left { type cyclic; } right { type cyclic; }'
            ' sides { type empty; }\n}\n' % (name, dims, n, body))

    write_scalar('T', shifted, '[0 0 0 1 0 0 0]')
    write_scalar('p', [p0] * n, '[1 -1 -2 0 0 0 0]')
    write_scalar('rho', rho, '[1 -3 0 0 0 0 0]')
    write_scalar('Cp', cp)
    for s in names:
        write_scalar(s, ys[s])
    (directory / 'U').write_text(
        'FoamFile\n{\n    version 2.0;\n    format ascii;\n    class volVectorField;\n'
        '    object U;\n}\n\ndimensions [0 1 -1 0 0 0 0];\n'
        'internalField uniform (%r 0 0);\n'
        'boundaryField\n{\n left { type cyclic; } right { type cyclic; }'
        ' sides { type empty; }\n}\n' % gen.VELOCITY)

    mesh = case / 'constant/polyMesh'
    mesh.mkdir(parents=True, exist_ok=True)
    points = '\n'.join('(%r 0 0)' % (i * dx) for i in range(n + 1))
    (mesh / 'points').write_text(
        'FoamFile\n{\n    version 2.0;\n    format ascii;\n    class vectorField;\n'
        '    object points;\n}\n\n%d\n(\n%s\n)\n;\n' % (n + 1, points))
    return advection_metrics.analyse(case, [directory.name])


class JanafHeatCapacity(unittest.TestCase):

    def test_cp_matches_the_enthalpy_derivative(self):
        """cp/R from the polynomial must be the T derivative of h/(R T)*T."""
        from metrics import janaf_cp_over_R, janaf_h_over_R

        coeffs = [3.3, 1.2e-3, -4.0e-7, 6.0e-11, -1.0e-15, -1000.0, 0.0]
        for temperature in (300.0, 1000.0, 2500.0):
            step = 1e-3 * temperature
            forward = janaf_h_over_R(coeffs, temperature + step)
            backward = janaf_h_over_R(coeffs, temperature - step)
            numeric = (forward - backward) / (2.0 * step)
            self.assertAlmostEqual(janaf_cp_over_R(coeffs, temperature) / numeric, 1.0,
                                   places=6)


if __name__ == '__main__':
    unittest.main()
