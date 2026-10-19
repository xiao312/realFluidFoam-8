import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from analyze import tracking, paired_difference
from gate import evaluate, LEVELS, STAGES
from prepare import prepare
from check import check_progress


class StudyTests(unittest.TestCase):
    def test_comparison_aligns_different_sampling_phases(self):
        def history(offset):
            return [dict(time_s=str(t), side=side, stage=stage, OH_level=str(level),
                         status='valid', speed_m_s=str(.06+1e4*t), x_m='.0019',
                         U_local='0', rho_local='20', rho_unburned='100')
                    for t in np.arange(0, 10e-6, 5e-7)+offset
                    for side in ['left', 'right'] for stage in STAGES for level in LEVELS]
        paired = paired_difference(history(0), history(2e-7), 2e-6, 8e-6)
        self.assertLess(max(v['max_abs_difference_cm_s'] for v in paired.values()), 1e-10)

    def test_completion_uses_solver_endpoint_not_output_phase(self):
        log = 'Time = 9.99834968798e-05\nCourant Number mean: 0.08 max: 0.084\nEnd\n'
        self.assertEqual(check_progress(log, 9.95834968798e-5,
                                       9.99834968798e-5, 1e-7, 5e-7), .084)
        with self.assertRaises(ValueError):
            check_progress(log.replace('End', ''), 9.95834968798e-5,
                           9.99834968798e-5, 1e-7, 5e-7)
        with self.assertRaises(ValueError):
            check_progress(log, 9.8e-5, 9.99834968798e-5, 1e-7, 5e-7)

    def test_gate_detects_stage_and_marker_disagreement(self):
        rows = [dict(time_s=str(t), side=side, stage=stage, OH_level=str(level),
                     status='valid', speed_m_s='.06')
                for t in [1e-6, 2e-6, 3e-6] for side in ['left', 'right']
                for stage in STAGES for level in LEVELS]
        self.assertEqual(evaluate(rows)['status'], 'PASS')
        for row in rows:
            if row['stage'] == STAGES[1] and float(row['OH_level']) == 1e-5:
                row['speed_m_s'] = '1.4'
        self.assertEqual(evaluate(rows)['status'], 'UNRESOLVED')
        self.assertAlmostEqual(evaluate(rows)['max_marker_spread_cm_s'], 134)

    def test_tracking_uses_local_velocity_density_and_front_sign(self):
        t = np.array([0, 1e-6, 2e-6])
        for side, sign in [('left', -1), ('right', 1)]:
            data = {'time_s': t, 'x_m': .002+sign*.4*t,
                    'U_local': np.full(3, sign*.1), 'rho_local': np.full(3, 20),
                    'rho_unburned': np.full(3, 100)}
            self.assertAlmostEqual(tracking(data, side)['local_density_weighted_cm_s'], 6)
            self.assertAlmostEqual(tracking(data, side)['laboratory_outward_cm_s'], 40)

    def test_copy_preserves_donor_and_changes_only_controls(self):
        # Keep even disposable verification files inside the operator workspace.
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[4]) as directory:
            root = Path(directory)
            donor = root/'jobs/124864929/case'
            (donor/'constant').mkdir(parents=True)
            (donor/'system').mkdir()
            (donor/'constant/flameSpeedProperties').write_text('interval 10;\nenabled true;')
            control = ('startFrom startTime;\nstartTime 0;\nendTime .0002;\ndeltaT 1e-7;\n'
                       'adjustTimeStep yes;\nwriteControl runTime;\nwriteInterval 1e-5;\n'
                       'runTimeModifiable yes;\nfunctions { monitor { type test; } }\n')
            (donor/'system/controlDict').write_text(control)
            for rank in range(8):
                (donor/f'processor{rank}/constant').mkdir(parents=True)
                time = donor/f'processor{rank}/7.99834968798e-05'
                time.mkdir()
                for field in ['T', 'p', 'U', 'OH', 'CH4', 'O2', 'N2']:
                    (time/field).write_text('fixture ' + field)
            job = root/'jobs/999'
            with contextlib.redirect_stdout(io.StringIO()):
                prepare('plan', job, 'dt25', root)
                self.assertFalse(job.exists())
                prepare('apply', job, 'dt25', root)
            self.assertEqual((donor/'system/controlDict').read_text(), control)
            data = json.loads((job/'case-inputs.json').read_text())
            self.assertEqual(data['diagnostic_interval_steps'], 20)
            self.assertEqual(data['controls']['writeInterval'], 200)
            self.assertNotIn('functions', (job/'case/system/controlDict').read_text())
            self.assertEqual((job/'case/processor0/7.99834968798e-05/OH').read_text(), 'fixture OH')
            with self.assertRaises(ValueError):
                prepare('apply', job, 'dt25', root)


if __name__ == '__main__':
    unittest.main()
