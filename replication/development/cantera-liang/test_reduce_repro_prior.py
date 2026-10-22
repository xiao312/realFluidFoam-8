#!/usr/bin/env python3
"""Unit tests for reduce_repro_prior.run on a synthetic previous-generation table."""
import json
import os
import tempfile
import unittest

import reduce_repro_prior as R


EXPECTED = {
    'reference_file': '/references/central-payload/assets/liang-8a-data.json',
    'reference_sha256': '0' * 64,
    'prior_source_commit': '9' * 40,
    'prior_module_archive_sha256': '1' * 64,
    'cli': 'liang-flame INPUTS CASE PHI NEW_OUTPUT',
    'points': [
        {'stage': 1, 'phi': 0.95, 'value_cm_s': 6.0, 'declared_job': '1',
         'declared_source': '9' * 40},
        {'stage': 2, 'phi': 0.95, 'value_cm_s': 6.5, 'declared_job': '2',
         'declared_source': '8' * 40},
        {'stage': 4, 'phi': 1.2, 'value_cm_s': 7.0, 'declared_job': '3',
         'declared_source': '8' * 40},
    ],
}


def write(path, text):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


class ReduceTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cases = os.path.join(self.dir, 'cases.txt')
        self.out = os.path.join(self.dir, 'out.json')
        self.expected = os.path.join(self.dir, 'expected.json')
        write(self.expected, json.dumps(EXPECTED))

    def reduce(self, text):
        write(self.cases, text)
        row = {'argv': ['--expected', self.expected, '--cases', self.cases, '--out', self.out]}
        old = __import__('sys').argv
        __import__('sys').argv = ['reduce_repro_prior.py'] + row['argv']
        try:
            R.main()
        finally:
            __import__('sys').argv = old
        return json.load(open(self.out, encoding='utf-8'))

    def test_reproduced_verdict(self):
        payload = self.reduce('1|0.95|99999999|0|31|410|6.0002\n2|0.95|88888888|0|180|402|6.5004\n'
                              '4|1.2|88888888|0|320|398|7.0006\n')
        self.assertEqual(payload['verdict'], 'reproduced')
        self.assertEqual(payload['stages']['2']['reproduced'], 1)
        self.assertAlmostEqual(payload['rows'][0]['delta_cm_s'], 0.0002, places=12)

    def test_harness_reproduced_but_staged_differs(self):
        payload = self.reduce('1|0.95|99999999|0|31|410|6.0001\n2|0.95|88888888|0|180|402|6.6000\n'
                              '4|1.2|88888888|0|320|398|7.9000\n')
        self.assertEqual(payload['verdict'], 'harness_reproduced_staged_model_differs')
        self.assertFalse(payload['rows'][2]['reproduced'])

    def test_under_refined_is_labelled(self):
        payload = self.reduce('1|0.95|99999999|0|31|410|6.0\n2|0.95|88888888|0|180|120|6.9\n'
                              '4|1.2|88888888|0|320|398|7.0\n')
        row = payload['rows'][1]
        self.assertEqual(row['reason'], 'under-refined grid')
        self.assertEqual(payload['verdict'], 'not_reproduced')

    def test_missing_point_is_incomplete(self):
        payload = self.reduce('1|0.95|99999999|0|31|410|6.0\n')
        self.assertEqual(payload['verdict'], 'incomplete')
        self.assertEqual(payload['missing'], [{'stage': 2, 'phi': 0.95},
                                              {'stage': 4, 'phi': 1.2}])

    def test_failed_case_is_recorded_not_hidden(self):
        payload = self.reduce('1|0.95|99999999|0|31|410|6.0\n2|0.95|88888888|124|900|-|-\n'
                              '4|1.2|88888888|0|320|398|7.0\n')
        row = payload['rows'][1]
        self.assertIsNone(row['delta_cm_s'])
        self.assertFalse(row['reproduced'])
        self.assertEqual(row['reason'], 'case did not complete')
        self.assertEqual(payload['verdict'], 'incomplete')

    def test_undeclared_point_is_an_error(self):
        with self.assertRaises(ValueError):
            self.reduce('3|1.1|88888888|0|100|400|7.0\n')

    def test_wrong_tree_is_rejected_not_compared(self):
        payload = self.reduce('1|0.95|88888888|0|31|410|6.0\n2|0.95|88888888|0|180|402|6.5\n'
                              '4|1.2|88888888|0|320|398|7.0\n')
        self.assertEqual(payload['verdict'], 'wrong_tree')
        self.assertFalse(payload['rows'][0]['tree_matches_declared'])
        self.assertIsNone(payload['rows'][0]['delta_cm_s'])
        self.assertEqual(payload['rows'][0]['reason'],
                         'run with a tree other than the one that declared this value')

    def test_per_point_declared_sources_are_kept(self):
        payload = self.reduce('1|0.95|99999999|0|31|410|6.0\n2|0.95|88888888|0|180|402|6.5\n'
                              '4|1.2|88888888|0|320|398|7.0\n')
        self.assertEqual(payload['prior_source_commits'], ['8' * 40, '9' * 40])
        self.assertEqual(payload['rows'][0]['declared_tree'], '99999999')
        self.assertEqual(payload['rows'][1]['declared_tree'], '88888888')

    def test_bad_width_is_an_error(self):
        with self.assertRaises(ValueError):
            self.reduce('1|0.95|99999999|0|31|410\n')


if __name__ == '__main__':
    unittest.main()
