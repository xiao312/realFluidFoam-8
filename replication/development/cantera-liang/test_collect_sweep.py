"""Tests for the sweep collector's identity checks."""
import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("collect_sweep", HERE / "collect_sweep.py")
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)


class ToleranceTest(unittest.TestCase):
    def test_half_a_unit_in_the_sixth_significant_digit(self):
        for value, expected in ((6.91036, 5e-6), (59.9906, 5e-5), (0.0069103, 5e-9)):
            self.assertAlmostEqual(sweep.printed_precision_tolerance(value) / expected, 1.0, places=8)

    def test_accepts_the_rounding_of_the_printed_value(self):
        printed = 6.91036
        for full in (6.910361763655559, 6.910356999999999, 6.9103635):
            self.assertLessEqual(abs(full - printed), sweep.printed_precision_tolerance(printed))

    def test_rejects_a_real_disagreement(self):
        printed = 6.91036
        # The uncoarsened-grid reference and the coarsened run differ by 1.4e-3 cm/s;
        # that is a different number, not stream rounding, and must still be rejected.
        self.assertGreater(abs(6.91177 - printed), sweep.printed_precision_tolerance(printed))

    def test_zero_speed_does_not_raise(self):
        self.assertGreater(sweep.printed_precision_tolerance(0.0), 0.0)


class LogLineTest(unittest.TestCase):
    def test_driver_prints_phi_without_a_decimal_point(self):
        found = sweep.COMPLETED.search('COMPLETED stage=1 phi=1 speed_cm_s=6.91036\n')
        self.assertIsNotNone(found)
        self.assertEqual(float(found.group(2)), 1.0)
        self.assertAlmostEqual(float(found.group(3)), 6.91036)

    def test_rejects_a_foreign_line(self):
        self.assertIsNone(sweep.COMPLETED.search('REFINED stage=1 phi=1 speed_cm_s=6.9'))


if __name__ == '__main__':
    unittest.main()
