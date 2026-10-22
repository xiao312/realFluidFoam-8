#!/usr/bin/env python3
"""Unit test for conductivity_attribution.py on a synthetic two-stage case."""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "conductivity_attribution.py")
FIELDS = ["x_m", "T_K", "rho_kg_m3", "cp_J_kgK", "lambda_W_mK"]


def write_profile(path, lam, rho=20.0, cp=1400.0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for i in range(6):
            writer.writerow({"x_m": 1e-4 * i, "T_K": 300.0 + 400.0 * i,
                             "rho_kg_m3": rho, "cp_J_kgK": cp, "lambda_W_mK": lam})


class ConductivityAttributionTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="liang8a-diag-")
        self.cases = os.path.join(self.root, "cases")
        for stage, lam in ((1, 0.10), (2, 0.10), (3, 0.10), (4, 0.116)):
            write_profile(os.path.join(self.cases, "stage-%d-phi-0.95" % stage,
                                       "result", "profile.csv"), lam)
        self.results = os.path.join(self.root, "results.json")
        json.dump({"results": [
            {"stage": 1, "phi": 0.95, "speed_cm_s": 6.0, "status": "CASE rc=0"},
            {"stage": 4, "phi": 0.95, "speed_cm_s": 6.6, "status": "CASE rc=0"},
            {"stage": 1, "phi": 1.0, "speed_cm_s": 9.9, "status": "CASE rc=0"},
        ]}, open(self.results, "w"))
        self.out = os.path.join(self.root, "out.json")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_script(self):
        env = dict(os.environ, FP_CASES=self.cases, FP_RESULTS=self.results,
                   FP_OUTPUT=self.out, FP_PHI="0.95")
        proc = subprocess.run([sys.executable, "-B", SCRIPT], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return json.load(open(self.out))

    def test_ratios_are_normalised_to_stage_1_at_the_requested_phi(self):
        data = self.run_script()
        stages = data["stages"]
        self.assertAlmostEqual(stages["1"]["speed_ratio"], 1.0, places=8)
        self.assertAlmostEqual(stages["1"]["lambda_ratio"], 1.0, places=8)
        self.assertAlmostEqual(stages["4"]["speed_ratio"], 1.1, places=8)
        self.assertAlmostEqual(stages["4"]["lambda_ratio"], 1.16, places=8)
        self.assertAlmostEqual(stages["4"]["alpha_ratio"], 1.16, places=8)
        self.assertAlmostEqual(stages["4"]["alpha_ratio_for_that_speed"], 1.21, places=8)

    def test_pointwise_block_covers_every_shared_point_and_keeps_the_sign(self):
        data = self.run_script()
        pointwise = data["pointwise"]
        self.assertEqual(pointwise["points"], 6)
        self.assertAlmostEqual(pointwise["mean_relative_conductivity_change"], 0.16, places=8)
        self.assertAlmostEqual(pointwise["min_relative_conductivity_change"], 0.16, places=8)
        self.assertAlmostEqual(pointwise["median_alpha_ratio"], 1.16, places=8)

    def test_inputs_are_recorded_so_the_analysis_is_reproducible(self):
        data = self.run_script()
        self.assertEqual(data["inputs"]["phi"], 0.95)
        self.assertEqual(os.path.realpath(data["inputs"]["cases"]), os.path.realpath(self.cases))


if __name__ == "__main__":
    unittest.main()
