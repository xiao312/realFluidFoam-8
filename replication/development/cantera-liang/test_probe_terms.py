#!/usr/bin/env python3
"""Tests for probe_terms.py: the term table must be arithmetic, not assertion."""
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / 'probe_terms.py'

HEADER = ('target_T,T,p_atm,rho_ideal,rho_srk,h_ideal,h_srk,lambda_mix_ideal,'
          'lambda_mix_srk,lambda_EH_molar,lambda_EH_mass,D_CH4_base,D_CH4_Taka,'
          'D_OH_base,D_OH_Taka,min_D_Taka,rate_L1_srk_over_ideal,'
          'concentration_srk_over_ideal,lambda_dense_increment,D_OH_bounded,'
          'min_D_bounded,pressure_rate_relative_error,D_H2_table2,D_H2_highT,'
          'D_OH_table2,D_OH_highT,D_CH4_table2,D_CH4_highT')


def probe_row(T, atm, base, full, dense):
    """One probe row with only the columns this reducer reads carrying meaning."""
    values = {
        'target_T': T, 'T': T, 'p_atm': atm, 'rho_ideal': 1.0, 'rho_srk': 2.0,
        'h_ideal': 0.0, 'h_srk': 0.0, 'lambda_mix_ideal': base, 'lambda_mix_srk': base,
        'lambda_EH_molar': full, 'lambda_EH_mass': full,
        'lambda_dense_increment': dense,
    }
    fields = HEADER.split(',')
    out = []
    for name in fields:
        out.append(repr(float(values.get(name, 1e-6))))
    return ','.join(out)


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.attribution = self.tmp / 'attribution.json'
        self.results = self.tmp / 'results.json'
        self.probe = self.tmp / 'probe.csv'
        self.out = self.tmp / 'terms.json'

    def write(self, exponent, median_change=0.20, alpha_ratio=None):
        speed3 = 6.0
        speed4 = speed3 * math.exp(exponent * math.log(1.0 + median_change))
        self.attribution.write_text(json.dumps({'pointwise': {
            'points': 10,
            'median_relative_conductivity_change': median_change,
            'median_alpha_ratio': alpha_ratio if alpha_ratio is not None else 1.0 + median_change,
        }}))
        self.results.write_text(json.dumps({'results': [
            {'stage': 3, 'phi': 0.95, 'speed_cm_s': speed3},
            {'stage': 4, 'phi': 0.95, 'speed_cm_s': speed4},
        ]}))
        lines = [HEADER]
        for T, base, factor in ((298.0, 0.027, 1.20), (900.0, 0.070, 1.15), (1.0, 1.0, 9.0)):
            atm = 1.0 if T == 1.0 else 100.0
            lines.append(probe_row(T, atm, base, base * factor, base * factor * 1.001))
        self.probe.write_text('\n'.join(lines) + '\n')

    def run_script(self, *extra):
        return subprocess.run([sys.executable, '-B', str(SCRIPT), '--probe', str(self.probe),
                               '--attribution', str(self.attribution), '--results',
                               str(self.results), '--out', str(self.out), *extra],
                              capture_output=True, text=True)

    def test_recovers_the_planted_exponent(self):
        self.write(exponent=0.75, median_change=0.20)
        done = self.run_script()
        self.assertEqual(done.returncode, 0, done.stderr)
        doc = json.loads(self.out.read_text())
        self.assertAlmostEqual(doc['summary']['sensitivity_dlnS_dlnalpha'], 0.75, places=9)
        self.assertEqual(doc['summary']['states_compared'], 2)  # the 1 atm row is not compared

    def test_predicted_step_matches_the_ratio_and_the_exponent(self):
        self.write(exponent=0.75, median_change=0.20)
        done = self.run_script()
        self.assertEqual(done.returncode, 0, done.stderr)
        doc = json.loads(self.out.read_text())
        median = doc['summary']['full']['median']
        expected = math.exp(0.75 * math.log(median)) - 1.0
        self.assertAlmostEqual(doc['summary']['predicted_step_full_median'], expected, places=12)
        # Each row's prediction must be its own ratio through the same exponent.
        for row in doc['table']:
            self.assertAlmostEqual(row['predicted_step_full'],
                                   math.exp(0.75 * math.log(row['ratio_full'])) - 1.0,
                                   places=12)

    def test_required_ratio_inverts_the_paper_step(self):
        self.write(exponent=1.0, median_change=0.20)
        done = self.run_script('--paper-step', '-0.10')
        self.assertEqual(done.returncode, 0, done.stderr)
        doc = json.loads(self.out.read_text())
        # With unit sensitivity the required conductivity ratio is 1 + step exactly.
        self.assertAlmostEqual(doc['summary']['required_ratio_for_paper_step'], 0.90, places=12)

    def test_non_positive_baseline_is_refused(self):
        self.write(exponent=1.0)
        rows = self.probe.read_text().replace('0.027', '0.0')
        self.probe.write_text(rows)
        done = self.run_script()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('non-positive denominator', done.stderr)

    def test_missing_solved_pair_is_refused(self):
        self.write(exponent=1.0)
        self.results.write_text(json.dumps({'results': [
            {'stage': 3, 'phi': 0.95, 'speed_cm_s': 6.0},
        ]}))
        done = self.run_script()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('no stage-3/stage-4 pair', done.stderr)


if __name__ == '__main__':
    unittest.main()
