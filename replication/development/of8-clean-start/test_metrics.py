"""Unit tests for the serial metric reader, using a synthetic case only.

Nothing here touches the network or a solver: a small block-shaped case with a
slab of hot products in the middle is written into a temporary directory, and the
metrics are checked against values that can be computed by hand.
"""
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics as M  # noqa: E402

REPO = HERE.parents[2]
THERMO = REPO / 'replication/validation/inputs/thermo.inputData_GRI'
CELLS = 200
LENGTH = 0.002
P0 = 10132500.0
T_COLD = 298.0
T_HOT = 2229.0


def flat(name, values):
    return ('FoamFile { version 2.0; format ascii; class volScalarField; object %s; }\n'
            'internalField nonuniform List<scalar>\n%d\n(\n%s\n);\n'
            % (name, len(values), '\n'.join(repr(float(v)) for v in values)))


def build_case(root):
    case = root / 'case'
    (case / 'constant/polyMesh').mkdir(parents=True)
    (case / 'constant').mkdir(exist_ok=True)
    (case / 'constant/thermo.inputData_GRI').write_text(THERMO.read_text())
    nodes = ["(%.17g 0 0)" % (LENGTH * i / CELLS) for i in range(CELLS + 1)]
    (case / 'constant/polyMesh/points').write_text(
        'FoamFile {}\n%d\n(\n%s\n)\n' % (len(nodes), '\n'.join(nodes)))

    names, table = M.species_table((case / 'constant/thermo.inputData_GRI').read_text())
    # cold methane/air on both sides, hot products in the middle third
    composition = {
        'CH4': [0.055, 0.0],
        'O2': [0.220, 0.0],
        'N2': [0.725, 0.725],
        'CO2': [0.0, 0.15],
        'H2O': [0.0, 0.12],
    }
    temperatures = []
    for i in range(CELLS):
        temperatures.append(T_HOT if CELLS // 3 <= i < 2 * CELLS // 3 else T_COLD)

    def state(index, temperature):
        hot = 1 if temperature == T_HOT else 0
        ys = {name: composition.get(name, [0.0, 0.0])[hot] for name in names}
        total = sum(ys.values())
        return {name: value / total for name, value in ys.items()}

    states = [state(i, t) for i, t in enumerate(temperatures)]
    density = []
    enthalpy = []
    for i, temperature in enumerate(temperatures):
        inverse_weight = sum(states[i][name] / table[name]['weight'] for name in names)
        density.append(P0 * (1.0 / inverse_weight) / (M.R_UNIVERSAL * temperature))
        enthalpy.append(sum(states[i][name] * M.sensible_enthalpy_MJ(table[name], temperature)
                            for name in names))

    for time_name in ('0', '1e-07'):
        directory = case / time_name
        directory.mkdir()
        (directory / 'T').write_text(flat('T', temperatures))
        (directory / 'p').write_text(flat('p', [P0] * CELLS))
        (directory / 'rho').write_text(flat('rho', density))
        (directory / 'he').write_text(flat('he', enthalpy))
        (directory / 'U').write_text(
            'FoamFile {}\ninternalField uniform (0 0 0);\n')
        for name in names:
            (directory / name).write_text(flat(name, [states[i][name] for i in range(CELLS)]))
    return case, table


class MetricsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.case, cls.table = build_case(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_metrics(self, case, times=''):
        out = Path(self.root) / 'metrics.json'
        command = [sys.executable, '-B', str(HERE / 'metrics.py'), '--case', str(case),
                   '--out', str(out)]
        if times:
            command += ['--times', times]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        return json.loads(out.read_text())

    def test_geometry(self):
        payload = self.run_metrics(self.case)
        geometry = payload['geometry']
        self.assertEqual(geometry['cells_from_points'], CELLS)
        self.assertAlmostEqual(geometry['dx_from_points'], LENGTH / CELLS, places=15)
        self.assertAlmostEqual(geometry['x_max'], LENGTH, places=15)

    def test_temperature_inversion_is_consistent(self):
        payload = self.run_metrics(self.case, times='0')
        inversion = payload['times'][0]['inversion']
        self.assertEqual(inversion['failed_cells'], 0)
        self.assertLess(inversion['max_rel_residual'], 1e-9)

    def test_ideal_gas_closure_and_fractions(self):
        row = self.run_metrics(self.case, times='0')['times'][0]
        self.assertLess(row['mass_fractions']['sum_error'], 1e-12)
        self.assertLess(row['mass_fractions']['ideal_gas_rho_max_rel_error'], 1e-12)
        self.assertGreaterEqual(row['mass_fractions']['min'], 0.0)
        self.assertLessEqual(row['mass_fractions']['max'], 1.0)

    def test_front_centroid_is_mid_domain(self):
        row = self.run_metrics(self.case, times='0')['times'][0]
        self.assertAlmostEqual(row['front']['density_deficit_position_m'], LENGTH / 2,
                               delta=LENGTH / CELLS)
        self.assertGreater(row['front']['peak_gradient_K_per_m'], 0.0)

    def test_repeated_state_conserves_mass_and_energy(self):
        payload = self.run_metrics(self.case, times='0,1e-07')
        self.assertEqual(len(payload['conservation_vs_first']), 2)
        for row in payload['conservation_vs_first']:
            self.assertLess(abs(row['mass_rel_change']), 1e-12)
            self.assertLess(abs(row['sensible_energy_rel_change']), 1e-12)

    def test_nonfinite_temperature_is_reported(self):
        case, _ = build_case(Path(self.root) / 'corrupt')
        text = (case / '0/T').read_text().replace(repr(T_HOT), 'nan', 1)
        (case / '0/T').write_text(text)
        row = self.run_metrics(case, times='0')['times'][0]
        self.assertFalse(row['finite']['all_finite'])

    def test_field_size_mismatch_is_rejected(self):
        case, _ = build_case(Path(self.root) / 'short')
        path = case / '0/p'
        text = path.read_text().replace(str(CELLS), str(CELLS + 1), 1)
        path.write_text(text)
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_metrics(case, times='0')


if __name__ == '__main__':
    unittest.main(verbosity=2)
