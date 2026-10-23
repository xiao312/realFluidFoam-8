#!/usr/bin/env python3
"""Tests for source_closure.py — the check that job 125301265 needed.

The run froze only `cantera-liang`, so `#include "../liang-properties/ElyHanley.H"` had no
target inside the archive and the build died three stages in. Both directions are pinned
here: a missing sibling header is a problem, an SDK include (`cantera/...`, supplied by
-I/opt/cantera-sdk/include) is not, and a path that escapes the layout root is reported.
"""
import json
import tempfile
import unittest
from pathlib import Path

import source_closure as sc


class ClosureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.layout = Path(self.tmp.name) / 'development'
        self.module = self.layout / 'cantera-liang'
        self.module.mkdir(parents=True)
        (self.layout / 'liang-properties').mkdir()
        (self.layout / 'liang-properties' / 'ElyHanley.H').write_text('// header\n')

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolvable_sibling_include_passes(self):
        (self.module / 'StagedTransport.h').write_text(
            '#include "../liang-properties/ElyHanley.H"\n#include <vector>\n')
        problems, stats = sc.check(self.module, self.layout)
        self.assertEqual(problems, [])
        self.assertEqual(stats['includes'], 1)

    def test_missing_sibling_include_is_a_problem(self):
        (self.layout / 'liang-properties' / 'ElyHanley.H').unlink()
        (self.module / 'StagedTransport.h').write_text(
            '#include "../liang-properties/ElyHanley.H"\n')
        problems, stats = sc.check(self.module, self.layout)
        self.assertEqual(len(problems), 1)
        self.assertIn('not in the frozen tree', problems[0])
        self.assertIn('../liang-properties/ElyHanley.H', problems[0])
        self.assertEqual(stats['problems'], 1)

    def test_sdk_include_is_not_a_problem(self):
        (self.module / 'flame.cpp').write_text(
            '#include "cantera/onedim.h"\n#include "cantera/base/Solution.h"\n')
        problems, stats = sc.check(self.module, self.layout)
        self.assertEqual(problems, [])
        self.assertEqual(stats['outside_layout'], 2)

    def test_escaping_the_layout_root_is_a_problem(self):
        outside = Path(self.tmp.name) / 'elsewhere'
        outside.mkdir()
        (outside / 'Far.H').write_text('// far\n')
        (self.module / 'bad.cpp').write_text('#include "../../elsewhere/Far.H"\n')
        problems, _ = sc.check(self.module, self.layout)
        self.assertEqual(len(problems), 1)
        self.assertIn('outside the layout root', problems[0])

    def test_local_includes_are_counted(self):
        (self.module / 'SrkKernel.h').write_text('// kernel\n')
        (self.module / 'alpha_probe.cpp').write_text('#include "SrkKernel.h"\n')
        problems, stats = sc.check(self.module, self.layout)
        self.assertEqual(problems, [])
        self.assertEqual(stats['includes'], 1)

    def test_cli_reports_status(self):
        out = Path(self.tmp.name) / 'closure.json'
        self.assertEqual(sc.main(['--module', str(self.module),
                                 '--layout-root', str(self.layout), '--json', str(out)]), 0)
        report = json.loads(out.read_text())
        self.assertEqual(report['problems'], 0)
        self.assertEqual(report['layout_root'], str(self.layout))
        (self.module / 'bad.cpp').write_text('#include "../missing/Nope.H"\n')
        self.assertEqual(sc.main(['--module', str(self.module),
                                 '--layout-root', str(self.layout)]), 1)


if __name__ == '__main__':
    unittest.main()
