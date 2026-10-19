import unittest
from analyze import measure


def front():
    # Manufactured constant-density front: U-v=0.06 m/s, gradY=2/m,
    # rho=10 => chemistry + diffusion = 1.2 kg/m3/s.
    return [dict(x=i*1e-5, y=0., z=0., YOH=y, rho=10., rhoSaved=10.,
                 gradOHx=2., magGradOH=2., omegaOH=2., minusDivJOH=-.8)
            for i, y in enumerate([0., 1e-5, 3e-5, 5e-5, 2e-5])]


class MeasurementTests(unittest.TestCase):
    def test_travelling_front_balance_and_diffusion_sign(self):
        result = measure(front(), 2e-5, cold_cells=1)
        self.assertAlmostEqual(result["direct_eq40_m_s"], .06)
        self.assertAlmostEqual(result["crossing"]["x"], 1.5e-5)
        self.assertAlmostEqual(result["chemistry_contribution_m_s"], .1)
        self.assertAlmostEqual(result["diffusion_contribution_m_s"], -.04)

    def test_missing_crossing(self):
        with self.assertRaisesRegex(ValueError, "crossing"):
            measure(front(), 1e-4, cold_cells=1)

    def test_nonfinite_input(self):
        rows = front(); rows[2]["omegaOH"] = float("nan")
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            measure(rows, 2e-5, cold_cells=1)

    def test_wrong_flank(self):
        rows = front()
        for row in rows: row["gradOHx"] = -2
        with self.assertRaisesRegex(ValueError, "flank"):
            measure(rows, 2e-5, cold_cells=1)

    def test_density_mismatch(self):
        rows = front(); rows[2]["rhoSaved"] = 9.
        with self.assertRaisesRegex(ValueError, "density disagree"):
            measure(rows, 2e-5, cold_cells=1)

    def test_provisional_report_retains_failure(self):
        rows = front(); rows[2]["rhoSaved"] = 9.
        result = measure(rows, 2e-5, cold_cells=1, report_density_mismatch=True)
        self.assertFalse(result["density_check_passed"])
        self.assertEqual(result["density_relative_tolerance"], 1e-7)

    def test_ambiguous_rising_crossing(self):
        rows = front()
        for row, value in zip(rows, [0., 3e-5, 1e-5, 4e-5, 5e-5]):
            row["YOH"] = value
        with self.assertRaisesRegex(ValueError, "crossing"):
            measure(rows, 2e-5, cold_cells=1)


if __name__ == "__main__":
    unittest.main()
