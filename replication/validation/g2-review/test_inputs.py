"""Parser fixtures only; these data are not CFD measurements or validation."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from inputs import averaging, image_grid, load_case, merge_samples, read_csv


class InputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_named_columns_and_split_files_preserve_values(self):
        a, b = self.root/'a.csv', self.root/'b.csv'
        a.write_text('# T,x\n300,0.0001\n400,0.0002\n')
        b.write_text('x,OH\n0.0001,0\n0.0002,0.01\n')
        fields = merge_samples([a, b])
        np.testing.assert_array_equal(fields['T'], [300, 400])
        np.testing.assert_array_equal(fields['OH'], [0, .01])
        b.write_text('x,OH\n0.0001,0\n0.0003,0.01\n')
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            merge_samples([a, b])

    def test_nonfinite_and_duplicate_headers_fail(self):
        path = self.root/'bad.csv'
        for text in ['x,T\n0,NaN\n', 'x,T,T\n0,300,400\n', 'x,T\n']:
            path.write_text(text)
            with self.assertRaises(ValueError):
                read_csv(path)

    def test_plane_retains_missing_grid_cell_and_rejects_off_grid_points(self):
        x, y = np.meshgrid(np.linspace(.0001, .1999, 3), np.linspace(.0001, .0248, 3))
        keep = np.arange(9) != 4
        fields = {'x': x.ravel()[keep], 'y': y.ravel()[keep], 'z': np.zeros(8), 'T': np.arange(8, dtype=float)}
        _, _, values = image_grid(fields, {'axialPoints': 3, 'radialPoints': 3}, 'T')
        self.assertEqual(np.ma.getmaskarray(values).sum(), 1)
        self.assertTrue(values.mask[1, 1])
        fields['x'][0] += .001
        with self.assertRaisesRegex(ValueError, 'not on'):
            image_grid(fields, {'axialPoints': 3, 'radialPoints': 3}, 'T')

    def test_mean_counters_are_not_assigned_to_another_time(self):
        report = {'time': .002, 'averaging': {'fields': {name: {'steps': 10, 'accumulatedTime_s': .001} for name in ('T', 'OH')}}}
        self.assertEqual(averaging(report, .002)['status'], 'producer-reported counters')
        self.assertEqual(averaging(report, .001)['status'], 'averaging counters unverified')
        self.assertFalse(averaging(report, .002)['statistical_convergence_established'])

    def test_case_selection_does_not_substitute_a_missing_requested_time(self):
        (self.root/'direct-g2-input.json').write_text(json.dumps({'observations': {'nearAxisRadius_m': .0001, 'radialPositions_m': [.03], 'imageGrid': None}}))
        target = self.root/'postProcessing/instantaneousProfiles/0.001'
        target.mkdir(parents=True)
        (target/'nearAxis_T_OH.csv').write_text('x,T,OH\n0.0001,300,0\n0.0002,400,0.01\n')
        data = load_case(self.root, None)
        self.assertEqual(len(data['records']), 1)
        self.assertIn('timeMeanProfiles', data['missing_categories'])
        partial = load_case(self.root, [.001, .002])
        self.assertEqual(partial['missing_requested_times']['instantaneousProfiles'], [.002])
        with self.assertRaisesRegex(ValueError, 'No selected'):
            load_case(self.root, [.002])


if __name__ == '__main__':
    unittest.main()
