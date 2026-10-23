"""Tests for the static model-range check.

The defect these pin down: the first version of `thermo_ranges` filtered thermo blocks by
the species list in the same file, and that list closes at the parenthesis in `CH2(S)`, so
only 14 of 53 species got a range and N2/AR were never checked against their own Tlow.

Run: python3 -B -m unittest test_model_range.py -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import admission  # noqa: E402
import model_range_check as mrc  # noqa: E402

GRI = Path('/workspace/forge-out/runs/of8-case-v1/case/constant')

SYNTHETIC = '''
thermoType
{
    type            hePsiThermo;
}

species
3
(
    H2
    CH2(S)
    N2
)

CH2(S)
{
    specie
    {
        molWeight       14.027;
    }
    thermodynamics
    {
        Tlow            250;
        Thigh           4000;
    }
}

N2
{
    specie
    {
        molWeight       28.0134;
    }
    thermodynamics
    {
        Tlow            200;
        Thigh           5000;
    }
}
'''


class ThermoRanges(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = Path(self.tmp)
        (self.dir / 'thermo.inputData_GRI').write_text(SYNTHETIC)

    def test_species_with_parenthesis_does_not_hide_later_blocks(self):
        ranges = admission.thermo_ranges(self.dir)
        self.assertEqual(set(ranges), {'CH2(S)', 'N2'})
        self.assertEqual(ranges['N2'], (200.0, 5000.0))
        self.assertEqual(ranges['CH2(S)'], (250.0, 4000.0))

    def test_state_below_floor_is_reported_per_species(self):
        problems = admission.state_range_problems(self.dir, 100.0, {'H2': 0.5, 'N2': 0.5})
        self.assertTrue(any('H2' in p and 'without a janaf range' in p for p in problems))
        self.assertTrue(any('N2 at 100 K is below' in p for p in problems))

    def test_state_inside_floor_passes(self):
        self.assertEqual(admission.state_range_problems(self.dir, 300.0, {'N2': 1.0}), [])

    def test_cli_exit_status_distinguishes_stop_from_unreadable(self):
        out = self.dir / 'verdict.json'
        rc = mrc.main(['--thermo', str(self.dir), '--temperature', '100',
                       '--composition', 'N2=1.0', '--json', str(out)])
        self.assertEqual(rc, 3)
        record = json.loads(out.read_text())
        self.assertEqual(record['verdict'], 'unsupported')
        self.assertEqual(record['checked_species'], {'N2': [200.0, 5000.0]})
        (self.dir / 'thermo.inputData_GRI').write_text('')
        self.assertEqual(mrc.main(['--thermo', str(self.dir), '--temperature', '300',
                                   '--composition', 'N2=1.0']), 2)


@unittest.skipUnless((GRI / 'thermo.inputData_GRI').exists(),
                     'GRI thermo table not staged in this workspace')
class FrozenGriTable(unittest.TestCase):
    def test_gri_table_covers_every_species(self):
        ranges = admission.thermo_ranges(GRI)
        self.assertEqual(len(ranges), 53)
        for name in ('H2', 'O2', 'H2O', 'N2', 'AR', 'CH4', 'CH2(S)'):
            self.assertIn(name, ranges)
        self.assertEqual({lo for lo, _ in ranges.values()}, {200.0})

    def test_the_ordered_cold_state_is_refused(self):
        """The supervisor order's 100 K H2/O2 interface, against the frozen GRI table."""
        problems = admission.state_range_problems(GRI, 100.0,
                                                 {'H2': 0.5, 'O2': 0.5, 'H2O': 0.0})
        self.assertEqual(len(problems), 2)
        for p in problems:
            self.assertIn('below its janaf range [200, 3500] K', p)


if __name__ == '__main__':
    unittest.main()
