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
import expected_energy as E  # noqa: E402

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

    def test_janaf_absolute_anchors(self):
        """Absolute checks the synthetic round-trip cannot make: the JANAF
        polynomial must reproduce published molar enthalpies.

        N2: h(1000 K) - h(298.15 K) = 21 463 J/mol (JANAF table; 28.0134 g/mol).
        N2: cp(1000 K) ~ 1169 J/(kg K).
        CH4: hf(298.15 K) = -74.87 kJ/mol, i.e. the a6 term is a real formation
        enthalpy and not a fitting constant to be dropped.
        """
        n2 = self.table['N2']
        self.assertEqual(M.sensible_enthalpy_MJ(n2, M.TREF), 0.0)
        h1000 = M.sensible_enthalpy_MJ(n2, 1000.0)
        self.assertAlmostEqual(h1000 / (21463.0 / 0.0280134), 1.0, delta=5e-3)
        cp = (M.sensible_enthalpy_MJ(n2, 1001.0) - M.sensible_enthalpy_MJ(n2, 999.0)) / 2.0
        self.assertAlmostEqual(cp / 1169.0, 1.0, delta=2e-2)

        import expected_energy as E
        hf_ch4 = E.formation_enthalpy(self.table['CH4']) * 0.016043
        self.assertAlmostEqual(hf_ch4 / -74870.0, 1.0, delta=1e-2)

    def test_ch4_and_o2_sensible_enthalpy_anchors(self):
        """Absolute sensible-enthalpy anchors from NIST Shomate coefficients.

        The GRI-3.0 file committed in this repo must reproduce published enthalpy
        increments. CH4 at 1000 K: NIST Shomate (298-1300 K coefficients) gives
        2.3797 MJ/kg; GRI gives 2.4092 (+1.24 percent), consistent with the known
        small inconsistency of the GRI CH4 enthalpy polynomial. O2 at 1000 K:
        NIST gives 709.6 kJ/kg and GRI 709.6 kJ/kg.

        This pins down a claim I made earlier and then could not reproduce: an
        expected CH4 increment of about 1.895 MJ/kg at 1000 K. There is no such
        value. 2.38-2.41 MJ/kg is the published increment, so the earlier number
        was my arithmetic error, not a defect in the table or the band switch at
        Tcommon = 1000 K.
        """
        thermo = Path(__file__).resolve().parent.parent.parent / 'validation/inputs/thermo.inputData_GRI'
        names, table = M.species_table(thermo.read_text())
        ch4_1000 = M.sensible_enthalpy_MJ(table['CH4'], 1000.0)
        self.assertAlmostEqual(ch4_1000 / 2.3797e6, 1.0, delta=2e-2)
        ch4_1500 = M.sensible_enthalpy_MJ(table['CH4'], 1500.0)
        self.assertAlmostEqual(ch4_1500 / 4.8708e6, 1.0, delta=3e-2)
        o2_1000 = M.sensible_enthalpy_MJ(table['O2'], 1000.0)
        self.assertAlmostEqual(o2_1000 / 7.096e5, 1.0, delta=1e-2)
        n2_1000 = M.sensible_enthalpy_MJ(table['N2'], 1000.0)
        self.assertAlmostEqual(n2_1000 / 7.6615e5, 1.0, delta=1e-3)

    def test_field_size_mismatch_is_rejected(self):
        case, _ = build_case(Path(self.root) / 'short')
        path = case / '0/p'
        text = path.read_text().replace(str(CELLS), str(CELLS + 1), 1)
        path.write_text(text)
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_metrics(case, times='0')


class EnergyAccountingTest(unittest.TestCase):
    """The declared total energy must include every term the solver's equation conserves.

    For sensibleEnthalpy the conserved quantity of the compressible energy equation is the
    total energy, E = sum(rho*(hs + hf - p/rho + 0.5*|u|^2))*V. Leave out the pressure term
    and the accounting disagrees with the solver by exactly the pressure work, which the
    closed-box caseA measures as a 5.8e-4 drift of the sensible enthalpy that is entirely
    accounted for by +0.366 J/m2 of sum(p*V).
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='energy-accounting-'))
        self.case = self.tmp / 'case'
        (self.case / '0').mkdir(parents=True)
        (self.case / 'constant').mkdir()
        n, self.dx = 32, 0.004 / 32
        species = {'CH4': 0.055, 'O2': 0.220, 'N2': 0.725}
        self.species = species
        thermo = ['FoamFile\n{\n}\n', 'species 3 (CH4 O2 N2);']
        for name, weight, hf in (('CH4', 16.043, -7.4892e7), ('O2', 31.998, 0.0),
                                 ('N2', 28.014, 0.0)):
            thermo.append('%s\n{\n    specie\n    {\n        molWeight %r;\n'
                          '        Tcommon 1000;\n'
                          '        lowCpCoeffs (3.0 1e-3 0 0 0 %r 0);\n'
                          '        highCpCoeffs (3.0 1e-3 0 0 0 %r 0);\n    }\n}'
                          % (name, weight, hf / (8314.46261815324 / weight),
                             hf / (8314.46261815324 / weight)))
        (self.case / 'constant' / 'thermo.inputData_GRI').write_text('\n'.join(thermo))

        def scalar(name, value, dims='[0 0 0 0 0 0 0]'):
            # a list, not uniform: cell_count() derives the cell count from the list size
            body = '\n'.join(repr(float(value)) for _ in range(n))
            (self.case / '0' / name).write_text(
                'FoamFile\n{\n}\n\ndimensions %s;\n'
                'internalField nonuniform List<scalar>\n%d\n(\n%s\n)\n;\n'
                % (dims, n, body))
        scalar('T', 1500.0, '[0 0 0 1 0 0 0]')
        scalar('p', 101325.0, '[1 -1 -2 0 0 0 0]')
        for name, fraction in species.items():
            scalar(name, fraction)
        (self.case / '0' / 'U').write_text(
            'FoamFile\n{\n}\n\ndimensions [0 1 -1 0 0 0 0];\n'
            'internalField uniform (0 0 0);\n')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_expected_total_energy_is_sensible_plus_formation_minus_pressure_volume(self):
        names, table = M.species_table(
            (self.case / 'constant' / 'thermo.inputData_GRI').read_text())
        expected = E.expected_from_initial_state(self.case, names, table, self.dx)
        recomposed = (expected['sensible_energy_J_per_m2']
                      + expected['formation_offset_J_per_m2']
                      - expected['pressure_volume_J_per_m2']
                      + expected['kinetic_energy_J_per_m2'])
        self.assertAlmostEqual(expected['total_energy_J_per_m2'], recomposed, places=12)
        self.assertAlmostEqual(expected['pressure_volume_J_per_m2'],
                               101325.0 * 0.004, places=9)
        self.assertAlmostEqual(expected['absolute_enthalpy_J_per_m2'],
                               expected['sensible_energy_J_per_m2']
                               + expected['formation_offset_J_per_m2'], places=12)
        # mass must match the ideal-gas state the solver starts from
        weight = 1.0 / sum(y / table[s]['weight'] for s, y in self.species.items())
        rho = 101325.0 * weight / (8314.46261815324 * 1500.0)
        self.assertAlmostEqual(expected['mass_kg_per_m2'], rho * 0.004, places=12)


if __name__ == '__main__':
    unittest.main(verbosity=2)
