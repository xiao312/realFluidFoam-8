"""Tests for the initial-profile coarsening used by the 100 atm Liang cases."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
STATEFUL = ['x_m', 'T_K', 'U_m_s', 'rho_kg_m3', 'Qdot_W_m3']
SPECIES = ['CH4', 'O2', 'N2']


def write_table(path, rows):
    header = STATEFUL + SPECIES
    path.write_text('\n'.join([','.join(header)] + [','.join(r) for r in rows]) + '\n')


def make_rows(count=200):
    rows = []
    for i in range(count):
        x = i / (count - 1)
        # A flame-like temperature rise, so a coarse node set has real interpolation error.
        t = 298.0 + 1500.0 / (1.0 + pow(2.718281828, -(x - 0.5) * 12.0))
        y = 1.0 - 0.9 * t / 1798.0
        rows.append(['%.16e' % x, '%.16e' % t, '0.1', '1.0', '0.0',
                     '%.16e' % (1.0 - y), '%.16e' % (0.21 * y), '%.16e' % (0.79 * y)])
    return rows


class CoarseningTest(unittest.TestCase):
    def run_tool(self, src_rows, points):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / 'src').mkdir()
        write_table(tmp / 'src' / 'guess.csv', src_rows)
        result = subprocess.run([sys.executable, '-B', str(HERE / 'prepare_guess.py'),
                                 str(tmp / 'src'), str(tmp / 'dst'),
                                 '--points', str(points)],
                                capture_output=True, text=True)
        return result, tmp / 'dst' / 'guess.csv'

    def test_retains_verbatim_rows_and_endpoints(self):
        rows = make_rows()
        result, out = self.run_tool(rows, 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = out.read_text().splitlines()
        self.assertEqual(len(lines), 41)
        self.assertEqual(lines[0], ','.join(STATEFUL + SPECIES))
        self.assertEqual(lines[1], ','.join(rows[0]))
        self.assertEqual(lines[-1], ','.join(rows[-1]))
        self.assertTrue(set(lines[1:]) <= {r for r in (rows and [','.join(r) for r in rows])})

    def test_reports_interpolation_error_of_the_coarse_nodes(self):
        result, out = self.run_tool(make_rows(), 60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('max_temperature_interpolation_error_K', result.stdout)

    def test_refuses_a_profile_it_cannot_represent(self):
        rows = make_rows()
        # Drop everything between 0.45 and 0.55 but keep the sharp temperature step,
        # then ask for very few points: the coarse nodes cannot follow the frozen curve.
        result, out = self.run_tool(rows, 3)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cannot', result.stderr + result.stdout)

    def test_refuses_negative_mass_fraction_beyond_round_off(self):
        rows = make_rows()
        rows[5][5] = '-1.0e-3'
        result, _ = self.run_tool(rows, 20)
        self.assertNotEqual(result.returncode, 0)

    def test_accepts_round_off_level_undershoot(self):
        rows = make_rows()
        rows[5][5] = '%.16e' % (float(rows[5][5]) - 3.0e-12)
        result, _ = self.run_tool(rows, 80)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_point_count_above_source_is_a_no_op(self):
        rows = make_rows(30)
        result, out = self.run_tool(rows, 100)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(out.read_text().splitlines()), 31)


if __name__ == '__main__':
    unittest.main()
