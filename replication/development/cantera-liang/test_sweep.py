"""Exercise qualification and duplicate guards without submitting real jobs."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sweep


class SweepGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ['release', 'sdk', 'build', 'inputs', 'jobs/123/result']:
            (self.root/name).mkdir(parents=True)
        (self.root/'build/build-passed.txt').touch()
        (self.root/'release/SOURCE_REVISION').write_text('test-source\n')
        self.phis = [.92, .95, 1., 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.44]
        for phi in self.phis:
            folder = self.root/'inputs'/f'phi{round(phi*100):03d}'
            folder.mkdir();(folder/'guess.csv').touch()
        (self.root/'inputs/plan.json').write_text(json.dumps([dict(phi=p, guess_phi=p) for p in self.phis]))
        self.ledger = self.root/'ledger.jsonl'
        self.ledger.write_text(''.join(json.dumps(dict(stage=2, phi=p))+'\n' for p in self.phis))
        result = self.root/'jobs/123/result'
        (result/'model-variant.txt').write_text('pressure-chemistry\n')
        (result/'pressure-Pa.txt').write_text('10132500\n')
        self.calls = []

    def invoke(self, pressure='100'):
        args = ['sweep.py', 'apply', str(self.root), *[str(self.root/n) for n in
                ['release', 'sdk', 'build', 'inputs', 'ledger.jsonl']], '2', '123',
                '--variant', 'pressure-chemistry', '--pressure-atm', pressure]
        def output(command, **kwargs):
            if command[0] != 'bash':
                return json.dumps(dict(stage=2))
            self.calls.append(command)
            return str(1000+len(self.calls))+'\n'
        with patch('sys.argv', args), patch('subprocess.check_output', side_effect=output), \
             patch('subprocess.run'), contextlib.redirect_stdout(io.StringIO()):
            sweep.main()

    @unittest.skipIf(__import__('sys').platform == 'win32', 'fcntl ledger locking is a Linux operation')
    def test_variant_is_distinct_and_reapply_does_not_duplicate(self):
        self.invoke();self.assertEqual(len(self.calls), 12)
        self.invoke();self.assertEqual(len(self.calls), 12)
        rows=[json.loads(line) for line in self.ledger.read_text().splitlines()]
        self.assertEqual(sum(r.get('variant')=='pressure-chemistry' for r in rows), 12)

    def test_pressure_mismatch_never_submits(self):
        with self.assertRaisesRegex(ValueError, 'variant/pressure'):
            self.invoke('1')
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
