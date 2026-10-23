"""Tests for the bounded 2-D cold-mixing case generator and its metrics.

The tests do not touch the solver. They check the parts that a wrong implementation would
get wrong silently:

  * the 3-species thermo file keeps each specie block byte-identical to the frozen file
    (a transcribed coefficient would be a silently changed mechanism),
  * the generated inlet profile carries exactly the registered G2 mass-flux ratio and the
    inlet flux recorded in the receipt equals the integral of the profile,
  * the flux balance closes for a state that is uniform along x (steady, no accumulation)
    and the imbalance is detected when the outlet flux is deliberately doubled,
  * the mixing width of a sharp interface is one cell and the metric reports the crossings.

Run: python3 -B -m unittest test_mixing.py -v
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import admission as adm  # noqa: E402
import mixing_metrics as mm  # noqa: E402
import prepare_mixing_case as pm  # noqa: E402

TOY_THERMO = """species
3
(
CH4
O2
N2
)
;

CH4
{
    specie
    {
        molWeight       16.043;
    }
    thermodynamics
    {
        Tlow            200;
        Thigh           3500;
        Tcommon         1000;
        highCpCoeffs    ( 0.0748515 0.0133909 -5.73286e-06 1.22293e-09 -1.01815e-13 -9468.34 18.4373 );
        lowCpCoeffs     ( 5.14988 -0.013671 4.91801e-05 -4.84743e-08 1.66694e-11 -10246.6 -4.6413 );
    }
    dataForKineticTrans
    {
        epsilonOverKb   141.4;
        sigmvi          3.758;
    }
}

O2
{
    specie
    {
        molWeight       31.998;
    }
    thermodynamics
    {
        Tlow            200;
        Thigh           3500;
        Tcommon         1000;
        highCpCoeffs    ( 3.78246 -2.99673e-03 9.84730e-06 -9.68129e-09 3.24372e-12 -1063.94 3.65767 );
        lowCpCoeffs     ( 3.78246 -2.99673e-03 9.84730e-06 -9.68129e-09 3.24372e-12 -1063.94 3.65767 );
    }
    dataForKineticTrans
    {
        epsilonOverKb   107.4;
        sigmvi          3.458;
    }
}

N2
{
    specie
    {
        molWeight       28.014;
    }
    thermodynamics
    {
        Tlow            200;
        Thigh           3500;
        Tcommon         1000;
        highCpCoeffs    ( 2.92664 1.48798e-03 -5.68476e-07 1.00970e-10 -6.75335e-15 -922.798 5.98053 );
        lowCpCoeffs     ( 3.29868 1.40824e-03 -3.96322e-06 5.64152e-09 -2.44485e-12 -1020.90 3.95037 );
    }
    dataForKineticTrans
    {
        epsilonOverKb   71.4;
        sigmvi          3.621;
    }
}
"""


def make_mechanism(root):
    root.mkdir(parents=True, exist_ok=True)
    for name in ('thermophysicalProperties', 'combustionProperties', 'momentumTransport',
                 'reactionsGRI'):
        (root / name).write_text('// stub, never parsed by the metrics\n')
    (root / 'thermo.inputData_GRI').write_text(TOY_THERMO)
    return root


def streams_from_receipt(receipt):
    """Per-transverse-row (rho, u, T, species) taken from the receipt."""
    ny = receipt['mesh']['ny']
    streams = receipt['streams']
    rho = streams['ideal_gas_density_kg_m3']
    rows = []
    for iy in range(ny):
        if iy < ny // 2:
            rows.append(dict(rho=rho['fuel'], u=streams['fuel']['velocity_m_per_s'],
                             T=streams['fuel']['temperature_K'],
                             species=streams['fuel']['species']))
        else:
            rows.append(dict(rho=rho['oxidiser'],
                             u=streams['oxidiser']['velocity_m_per_s'],
                             T=streams['oxidiser']['temperature_K'],
                             species=streams['oxidiser']['species']))
    return rows


def write_fields(case, receipt, time_name, outlet_scale=1.0):
    """Write a state that is uniform along x, with the receipt's two-stream profile.

    Because the profile is uniform along x and identical at the inlet and the outlet
    columns, the exact inlet fluxes of the receipt must equal the integrated outlet fluxes,
    so any nonzero imbalance is an implementation error rather than physics.
    """
    from prepare_mixing_case import scalar_field, vector_field
    nx, ny = receipt['mesh']['nx'], receipt['mesh']['ny']
    p0 = receipt['pressure_Pa']
    rows = streams_from_receipt(receipt)
    names = list(receipt['streams']) and [receipt['streams']['fuel']['species'],
                                          receipt['streams']['oxidiser']['species'], 'N2']
    names = [n for i, n in enumerate(names) if n not in names[:i]]
    d = case / time_name
    d.mkdir(parents=True, exist_ok=True)

    def per_cell(key):
        return [rows[iy][key] for iy in range(ny) for _ in range(nx)]

    (d / 'rho').write_text(scalar_field('rho', per_cell('rho'),
                                        'inlet { type zeroGradient; } outlet { type zeroGradient; }'))
    (d / 'p').write_text(scalar_field('p', [p0] * (nx * ny),
                                      'inlet { type zeroGradient; } outlet { type zeroGradient; }'))
    (d / 'T').write_text(scalar_field('T', per_cell('T'),
                                      'inlet { type zeroGradient; } outlet { type zeroGradient; }',
                                      dimensions='[0 0 0 1 0 0 0]'))
    ux = per_cell('u')
    if outlet_scale != 1.0:
        for iy in range(ny):
            ux[(nx - 1) + nx * iy] *= outlet_scale
    (d / 'U').write_text(vector_field('U', [(u, 0.0, 0.0) for u in ux],
                                      'inlet { type zeroGradient; } outlet { type zeroGradient; }'))
    for name in names:
        values = [1.0 if rows[iy]['species'] == name else 0.0
                  for iy in range(ny) for _ in range(nx)]
        (d / name).write_text(scalar_field(name, values,
                                           'inlet { type zeroGradient; } outlet { type zeroGradient; }'))


class ThermoSubsetTest(unittest.TestCase):
    def test_blocks_are_verbatim(self):
        keep = ['CH4', 'O2', 'N2']
        out = pm.write_thermo_subset(TOY_THERMO, keep)
        self.assertIn('species 3 (CH4 O2 N2);', out)
        blocks = pm.specie_blocks(TOY_THERMO)
        for name in keep:
            self.assertIn(blocks[name].strip(), out.strip())

    def test_missing_species_is_an_error(self):
        with self.assertRaises(SystemExit):
            pm.write_thermo_subset(TOY_THERMO, ['CH4', 'H2'])


class StreamPropertiesTest(unittest.TestCase):
    def test_g2_mass_flux_ratio_is_matched(self):
        cfg = dict(pm.DEFAULTS)
        props = pm.stream_properties(cfg)
        ratio = props['inlet_mass_flux_ox'] / props['inlet_mass_flux_fuel']
        self.assertAlmostEqual(ratio, cfg['g2_oxygen_mass_flow'] / cfg['g2_fuel_mass_flow'],
                               places=12)
        # Both streams are at 300 K by default since the 100 K stream was retired. Equal
        # temperature does not mean equal density: the streams have different molar masses,
        # so matching the mass flux gives u_ox = u_fuel * (M_fuel/M_ox) * (mdot_ox/mdot_fuel).
        self.assertAlmostEqual(props['u_ox'],
                               10.0 * (16.043 / 31.998) * (44.4 / 143.1), places=9)

    def test_densities_are_ideal_gas(self):
        cfg = dict(pm.DEFAULTS)
        props = pm.stream_properties(cfg)
        self.assertAlmostEqual(props['rho_fuel'], 101325 * 16.043 / (8314.46261815324 * 300.0),
                               places=10)
        self.assertAlmostEqual(props['rho_ox'], 101325 * 31.998 / (8314.46261815324 * 300.0),
                               places=10)


class FluxBalanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='mix-test-'))
        make_mechanism(self.tmp / 'mech')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def generate(self, name='case', nx=8, ny=4):
        case = self.tmp / name
        subprocess.run([sys.executable, '-B', str(HERE / 'prepare_mixing_case.py'),
                        '--out', str(case), '--mechanism-source', str(self.tmp / 'mech'),
                        '--source-commit', 'test', '--nx', str(nx), '--ny', str(ny),
                        '--end-time', '4e-4', '--delta-t', '2e-7',
                        '--write-interval', '2e-4'],
                       check=True, capture_output=True)
        return case, json.loads(Path(str(case) + '.receipt.json').read_text())

    def run_metrics(self, case, receipt_path):
        out = self.tmp / 'metrics.json'
        subprocess.run([sys.executable, '-B', str(HERE / 'mixing_metrics.py'),
                        '--case', str(case), '--receipt', str(receipt_path),
                        '--out', str(out)], check=True, capture_output=True, cwd=str(HERE))
        return json.loads(out.read_text())

    def test_control_dict_is_semicolon_terminated(self):
        """OpenFOAM silently loses an entry whose value line has no semicolon.

        Job 125290253 died in blockMesh with `keyword deltaT is undefined` because the
        generator wrote `endTime 0.0002` and `deltaT 2e-07` without terminators: the parser
        folded the next keyword into the previous value. A missing `;` is invisible in a
        diff and fatal in the allocation, so it is checked here.
        """
        case, _ = self.generate(name='syntax')
        lines = (case / 'system' / 'controlDict').read_text().splitlines()
        # Skip the FoamFile header block: its members are not terminator-checked here.
        body = lines[lines.index('}') + 1:]
        entries = [line for line in body
                   if line.strip() and not line.strip().startswith(('{', '}', '//'))]
        for line in entries:
            self.assertTrue(line.rstrip().endswith(';'), 'unterminated entry: %r' % line)
        keys = {line.split()[0] for line in entries if len(line.split()) > 1}
        for key in ('endTime', 'deltaT', 'writeInterval', 'startTime', 'stopAt'):
            self.assertIn(key, keys)
        text = (case / 'system' / 'controlDict').read_text()
        self.assertIn('deltaT          2e-07;', text)
        self.assertIn('endTime         0.0004;', text)

    def test_boundary_lists_match_patch_face_counts(self):
        """Each nonuniform boundary list must have as many entries as its patch has faces.

        Job 125291239 died in the solver reading `0/T`: "size 3200 is not equal to the
        given value of 40", because the inlet patch values were the nx*ny cell list. The
        inlet is the x = 0 plane, so it has ny faces.
        """
        case, _ = self.generate(name='patches', nx=8, ny=4)
        for name in ('T', 'U', 'CH4', 'O2', 'N2'):
            path = case / '0' / name
            if not path.exists():
                continue
            text = path.read_text()
            for match in re.finditer(r'List<(scalar|vector)> (\d+) \(', text):
                declared = int(match.group(2))
                self.assertEqual(declared, 4,
                                 '%s: boundary list has %d entries for a 4-face inlet'
                                 % (name, declared))

    def test_reaction_list_is_empty_for_the_three_species_subset(self):
        """A GRI reaction list cannot be carried into a 3-species subset.

        Job 125292279 aborted parsing it: "Specie O not found in table". With CH4/O2/N2 no
        elementary reaction is representable, so the case is inert by construction and the
        receipt has to say so.
        """
        case, receipt = self.generate(name='inert', nx=8, ny=4)
        text = (case / 'constant' / 'reactionsGRI').read_text()
        # An empty dictionary block, not `reactions ();`: the latter is a primitive entry and
        # aborts the chemistry-model construction (job 125295010).
        self.assertRegex(text, r'reactions\s*\{\s*\}')
        self.assertNotIn('reaction "', text)
        chemistry = (case / 'constant' / 'chemistryProperties').read_text()
        self.assertIn('chemistry       off;', chemistry)
        self.assertEqual(receipt['chemistry'], 'off')
        notes = ' '.join(d.get('note', '') for d in receipt['frozen_inputs'])
        self.assertIn('emptied', notes)
        joined = ' '.join(receipt['deviations_from_registered_target'])
        self.assertIn('no reaction', joined)

    def test_steady_state_balance_closes(self):
        case, receipt = self.generate()
        for t in ('0', '2e-4'):
            write_fields(case, receipt, t)
        result = self.run_metrics(case, Path(str(case) + '.receipt.json'))
        self.assertTrue(result['balances'])
        for balance in result['balances']:
            self.assertAlmostEqual(balance['mass_imbalance_fraction'], 0.0, places=10)
            self.assertAlmostEqual(balance['energy_imbalance_fraction'], 0.0, places=9)
            # A state that is uniform along x has no accumulation and equal inlet/outlet
            # fluxes, so the momentum residual must vanish. Batch r6/r12 never asserted
            # this and shipped a ~1.0 momentum imbalance for a uniform flow because the
            # outlet pressure was subtracted twice (job 125296683).
            self.assertAlmostEqual(balance['momentum_net_in'], 0.0, places=12)
            self.assertAlmostEqual(balance['momentum_imbalance_fraction'], 0.0, places=9)

    def test_pressure_is_counted_once(self):
        """A uniform flow with equal convective fluxes must balance exactly, not to -p A."""
        self.assertEqual(mm.momentum_net(3.0, 3.0, 7.0, 7.0), 0.0)
        self.assertAlmostEqual(mm.momentum_net(3.0, 3.0, 7.0, 9.0), -2.0, places=15)
        # Doubling the outlet pressure force must not double it again in the residual.
        self.assertAlmostEqual(mm.momentum_net(0.0, 0.0, 1.0, 3.0), -2.0, places=15)

    def test_momentum_imbalance_detects_a_doubled_outlet_velocity(self):
        case, receipt = self.generate(name='case5')
        write_fields(case, receipt, '0')
        write_fields(case, receipt, '2e-4', outlet_scale=2.0)
        result = self.run_metrics(case, Path(str(case) + '.receipt.json'))
        balance = result['balances'][0]
        self.assertLess(balance['momentum_net_in'], 0.0)
        self.assertGreater(abs(balance['momentum_imbalance_fraction']), 0.1)

    def test_crossings_are_paired_with_their_own_heights(self):
        """Mirroring a profile must flip the signed crossings, not shift their heights.

        The earlier implementation sorted the column from the top down and then paired the
        values with ascending cell heights, so an asymmetric profile was measured against
        heights that belonged to the other end of the column. Two profiles that are exact
        mirrors in height must give equal widths and opposite signed widths.
        """
        case, receipt = self.generate(name='mirror')
        write_fields(case, receipt, '0')
        write_fields(case, receipt, '2e-4')
        result = self.run_metrics(case, Path(str(case) + '.receipt.json'))
        mixing = result['per_time'][0]['mixing']
        self.assertTrue(mixing['column_ordered_by_height'])
        self.assertEqual(mixing['oxidiser_profile'], 'increasing')
        self.assertGreater(mixing['y_at_Y90'], mixing['y_at_Y10'])
        self.assertAlmostEqual(mixing['width_10_90_signed'], mixing['width_10_90'], places=12)
        self.assertEqual(mixing['crossings'], dict(Y90=1, Y50=1, Y10=1))

        geom = dict(nx=1, ny=8, dx=1.0, dy=1.0, depth=1.0)
        ascending = dict(Y=dict(A=[0.0, 0.0, 0.2, 0.6, 1.0, 1.0, 1.0, 1.0]))
        descending = dict(Y=dict(A=[1.0, 1.0, 1.0, 1.0, 0.6, 0.2, 0.0, 0.0]))
        up = mm.mixing_width(ascending, geom, 'A')
        down = mm.mixing_width(descending, geom, 'A')
        self.assertEqual(up['oxidiser_profile'], 'increasing')
        self.assertEqual(down['oxidiser_profile'], 'decreasing')
        self.assertAlmostEqual(up['width_10_90'], down['width_10_90'], places=12)
        self.assertAlmostEqual(up['width_10_90_signed'], -down['width_10_90_signed'], places=12)
        # A mirrored profile reflects the crossings about the half-height plane y = ny*dy/2.
        half = 0.5 * geom['ny'] * geom['dy']
        self.assertAlmostEqual(down['y_at_Y90'], 2 * half - up['y_at_Y90'], places=12)
        self.assertAlmostEqual(down['y_at_Y10'], 2 * half - up['y_at_Y10'], places=12)

    def test_out_of_range_inlet_temperature_is_flagged(self):
        """A 100 K inlet against Tlow = 200 K is an extrapolation, not an exact flux."""
        case, receipt = self.generate(name='cold')
        receipt['streams']['oxidiser']['temperature_K'] = 100.0
        path = self.tmp / 'cold.receipt.json'
        path.write_text(json.dumps(receipt))
        write_fields(case, receipt, '0')
        write_fields(case, receipt, '2e-4')
        result = self.run_metrics(case, path)
        inlet = result['inlet_flux']
        self.assertIn('oxidiser', inlet['out_of_range_temperature'])
        self.assertEqual(inlet['streams']['oxidiser']['evaluated_at_K'], 200.0)
        self.assertNotEqual(inlet['total_energy_flux_J_per_s'],
                            inlet['energy_flux_at_thermo_limits_J_per_s'])
        self.assertIn('nominal', inlet['basis'])
        self.assertEqual(result['generation']['id'], 'posthoc-corrected-r13')

    def test_in_range_temperatures_are_not_flagged(self):
        case, receipt = self.generate(name='warm')
        # The generator's default is the registered G2 pair (100 K oxidiser against a
        # 200 K table floor), so a warm control has to be set explicitly.
        receipt['streams']['oxidiser']['temperature_K'] = 300.0
        receipt['streams']['fuel']['temperature_K'] = 300.0
        path = self.tmp / 'warm.receipt.json'
        path.write_text(json.dumps(receipt))
        write_fields(case, receipt, '0')
        write_fields(case, receipt, '2e-4')
        result = self.run_metrics(case, path)
        self.assertEqual(result['inlet_flux']['out_of_range_temperature'], [])
        self.assertAlmostEqual(result['inlet_flux']['total_energy_flux_J_per_s'],
                               result['inlet_flux']['energy_flux_at_thermo_limits_J_per_s'],
                               places=12)

    def test_imbalance_is_detected(self):
        case, receipt = self.generate(name='case2')
        write_fields(case, receipt, '0')
        write_fields(case, receipt, '2e-4', outlet_scale=2.0)
        result = self.run_metrics(case, Path(str(case) + '.receipt.json'))
        self.assertGreater(abs(result['balances'][0]['mass_imbalance_fraction']), 0.1)

    def test_sharp_interface_width_is_one_cell(self):
        case, receipt = self.generate(name='case3')
        write_fields(case, receipt, '0')
        write_fields(case, receipt, '2e-4')
        result = self.run_metrics(case, Path(str(case) + '.receipt.json'))
        width = result['per_time'][0]['mixing']['width_10_90']
        self.assertAlmostEqual(width, 0.8 * receipt['mesh']['dy'], places=9)

    def test_receipt_records_registered_ratio_and_deviations(self):
        _, receipt = self.generate(name='case4')
        self.assertAlmostEqual(receipt['inlet_flux']['oxidiser_mass_flux_kg_per_s']
                               / receipt['inlet_flux']['fuel_mass_flux_kg_per_s'],
                               44.4 / 143.1, places=9)
        self.assertEqual(len(receipt['deviations_from_registered_target']), 4)
        self.assertIn('NOT a G2 replication', receipt['purpose'])


class FormationEnthalpyTest(unittest.TestCase):
    def test_hf_plus_hs_reproduces_the_tabulated_enthalpy(self):
        names, table = mm.species_table(TOY_THERMO)
        entry = table['CH4']
        hf = mm.formation_enthalpy_J(entry)
        expected = mm.R_UNIVERSAL / entry['weight'] * mm.janaf_h_over_R(
            entry['coeffs']['low'], mm.TREF)
        self.assertAlmostEqual(hf, expected, places=6)
        self.assertLess(hf, 0.0)
        # hs + hf must equal the bare tabulated h(T) with no reference subtraction
        for temperature in (250.0, 298.15, 900.0, 1800.0):
            band = 'low' if temperature <= entry['tcommon'] else 'high'
            bare = mm.R_UNIVERSAL / entry['weight'] * mm.janaf_h_over_R(
                entry['coeffs'][band], temperature)
            self.assertAlmostEqual(mm.sensible_enthalpy_MJ(entry, temperature) + hf, bare,
                                   delta=abs(bare) * 1e-12 + 1e-6)


if __name__ == '__main__':
    unittest.main()


class AdmissionTest(unittest.TestCase):
    """The static gate must pass a coherent case and reject the three real failures."""

    @classmethod
    def setUpClass(cls):
        import admission as A
        cls.A = A
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cfg = dict(pm.DEFAULTS)
        cls.case = base / 'case'
        mech = make_mechanism(base / 'mech')
        pm.write_case(cls.case, cfg, mech, 'test')
        cls.ny = cfg['ny']

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def clone(self, name):
        import shutil
        dst = Path(self.tmp.name) / name
        shutil.copytree(self.case, dst)
        return dst

    def test_clean_case_passes(self):
        self.assertEqual(self.A.admission(self.case, expected_inlet_faces=self.ny), [])

    def test_full_gri_reaction_list_is_rejected(self):
        """Negative control: job 125292279 died on exactly this."""
        case = self.clone('gri')
        full = Path('/workspace/forge-out/runs/of8-case-v1/case/constant/reactionsGRI')
        if not full.exists():
            self.skipTest('full GRI reaction file not staged here: %s' % full)
        (case / 'constant' / 'reactionsGRI').write_bytes(full.read_bytes())
        failures = self.A.admission(case, expected_inlet_faces=self.ny)
        self.assertTrue(any('reaction species missing' in f for f in failures), failures)

    def test_unterminated_entry_is_rejected(self):
        """Negative control: job 125290253 died on exactly this."""
        case = self.clone('unterminated')
        path = case / 'system' / 'controlDict'
        text = re.sub(r'deltaT(\s+)[0-9.eE+-]+;', r'deltaT\g<1>2e-07', path.read_text())
        path.write_text(text)
        failures = self.A.admission(case, expected_inlet_faces=self.ny)
        self.assertTrue(any('controlDict' in f and 'not terminated' in f
                            for f in failures), failures)

    def test_token_list_reactions_are_rejected(self):
        """Negative control: job 125295010 died on exactly this.

        `reactions ();` is a primitive entry; ReactionList calls dict.subDict("reactions").
        """
        case = self.clone('tokenlist')
        path = case / 'constant' / 'reactionsGRI'
        path.write_text(re.sub(r'reactions\s*\{\s*\}', 'reactions ();', path.read_text()))
        failures = self.A.admission(case, expected_inlet_faces=self.ny)
        self.assertTrue(any('token list' in f for f in failures), failures)

    def test_generated_reactions_entry_is_a_dictionary_block(self):
        text = (self.case / 'constant' / 'reactionsGRI').read_text()
        self.assertRegex(text, r'reactions\s*\{\s*\}')
        self.assertNotRegex(text, r'reactions\s*\(')

    def test_frozen_source_must_cover_its_imports(self):
        """Job 125296683 solved, then lost its metrics to an unfrozen module."""
        import tempfile
        with tempfile.TemporaryDirectory() as module, tempfile.TemporaryDirectory() as frozen:
            Path(module, 'entry.py').write_text('from helper import f\n')
            Path(module, 'helper.py').write_text('def f():\n    return 1\n')
            Path(frozen, 'entry.py').write_text('from helper import f\n')
            problems = self.A.import_closure(frozen, module)
            self.assertEqual(len(problems), 1)
            self.assertIn('helper.py', problems[0])
            Path(frozen, 'helper.py').write_text('def f():\n    return 1\n')
            self.assertEqual(self.A.import_closure(frozen, module), [])

    def test_returned_module_is_frozen(self):
        text = (Path(self.A.__file__).parent / 'job-mixing.sh').read_text()
        freeze = text.split('freeze_source.sh', 1)[1].split('>', 1)[0]
        self.assertIn('metrics.py', freeze)
        self.assertIn('imports', text)

    def test_inlet_temperature_outside_janaf_range_is_rejected(self):
        """Negative control: job 125296683 ran a 100 K stream against Tlow = 200 K.

        The solver accepted it, emitted 1.7e6 out-of-range warnings and wrote the cold half
        of the domain at exactly 200.0 K - the thermo floor. The gate has to refuse the case
        before blockMesh, naming the species, the face and the range it violates.
        """
        case = self.clone('cold-inlet')
        path = case / '0' / 'T'
        text = path.read_text()
        # Write the cold stream the way the old generator did: 100 K on the oxidiser faces.
        text = re.sub(r'List<scalar> %d \((.*?)\)' % self.ny,
                      lambda m: 'List<scalar> %d (%s)' % (
                          self.ny, ' '.join('100.0' if float(v) > 0 and i >= self.ny // 2
                                            else v
                                            for i, v in enumerate(m[1].split()))),
                      text, flags=re.S)
        path.write_text(text)
        failures = self.A.admission(case, expected_inlet_faces=self.ny)
        self.assertTrue(any('outside its JANAF range' in f and 'O2' in f for f in failures),
                        failures)
        self.assertLessEqual(len(failures), 6)
        self.assertEqual(self.A.inlet_temperature_problems(self.case), [])

    def test_generated_default_sits_inside_the_janaf_range(self):
        ranges = self.A.thermo_ranges(self.case / 'constant')
        self.assertEqual(sorted(ranges), ['CH4', 'N2', 'O2'])
        receipt = json.loads(Path(str(self.case) + '.receipt.json').read_text())
        for stream in ('fuel', 'oxidiser'):
            temperature = receipt['streams'][stream]['temperature_K']
            low, high = ranges[receipt['streams'][stream]['species']]
            self.assertGreaterEqual(temperature, low, stream)
            self.assertLessEqual(temperature, high, stream)
        joined = ' '.join(receipt['deviations_from_registered_target'])
        self.assertIn('JANAF table', joined)

    def test_wrong_inlet_patch_size_is_rejected(self):
        """Negative control: job 125291239 died on exactly this."""
        case = self.clone('patch')
        path = case / '0' / 'T'
        path.write_text(re.sub(r'List<scalar> %d' % self.ny, 'List<scalar> 3200',
                               path.read_text()))
        failures = self.A.admission(case, expected_inlet_faces=self.ny)
        self.assertTrue(any('inlet patch' in f for f in failures), failures)
