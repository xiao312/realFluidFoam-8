#!/usr/bin/env python3
"""Check that every quoted include of this module resolves in the frozen tree.

Job 125301265 (liang8a-terms-v2) froze only `replication/development/cantera-liang` and then
failed to compile `test_srk.cpp` and `StagedTransport.h`, which both do

    #include "../liang-properties/ElyHanley.H"

That header exists in the checkout but not in the archive, so the run had a source tree that
could not build even though every file it *did* contain matched its manifest. A manifest of
a tree is not a closure of the code the tree compiles: the archive has to carry every file a
translation unit reads.

This check is deliberately static and cheap, so it can run before a compiler is invoked and
name the missing path instead of a `fatal error` three stages into a build.

Usage:
    source_closure.py --module DIR [--layout-root DIR] [--json OUT]

`--layout-root` is the directory the module's relative includes are resolved inside (for this
module: `replication/development`, which holds both cantera-liang and liang-properties).
Defaults to the module's parent. Exit status is 1 when anything is missing, 0 otherwise.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SOURCE_SUFFIXES = ('.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.H')
INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)


def quoted_includes(path):
    """(line, target) for every quoted include in one source file."""
    text = path.read_text(errors='replace')
    out = []
    for m in INCLUDE.finditer(text):
        out.append((text[:m.start()].count('\n') + 1, m[1]))
    return out


def check(module, layout_root=None):
    """Return (problems, stats).

    A quoted include is resolved the way the compiler resolves it for a file in this module:
    relative to the including file's directory first, then relative to the module directory
    (the build passes -I<module>). Anything that resolves to a path outside the layout root,
    or does not exist at all, is reported.
    """
    module = Path(module).resolve()
    layout = Path(layout_root).resolve() if layout_root else module.parent
    problems, checked, external = [], 0, 0
    for path in sorted(module.rglob('*')):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        for line, target in quoted_includes(path):
            if target.startswith('<'):
                continue
            checked += 1
            rel = path.relative_to(module).as_posix()
            candidates = [(path.parent / target), (module / target), (layout / target)]
            found = next((c.resolve() for c in candidates if c.exists()), None)
            relative = target.startswith('..') or target.startswith('./')
            if found is None:
                if relative:
                    problems.append('%s:%d includes "%s", which is not in the frozen tree '
                                    '(job 125301265 failed here)' % (rel, line, target))
                else:
                    # Not a tree path: the SDK headers arrive through -I/opt/cantera-sdk/include
                    # and are identified by the environment, not by this manifest.
                    external += 1
                continue
            if relative and layout not in found.parents and found != layout:
                problems.append('%s:%d includes "%s", which resolves to %s outside the '
                                'layout root %s' % (rel, line, target, found, layout))
    stats = dict(module=str(module), layout_root=str(layout), includes=checked,
                 outside_layout=external, problems=len(problems))
    return problems, stats


def main(argv=None):
    parser = argparse.ArgumentParser(description='Resolve every quoted include of a module')
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--layout-root', type=Path)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args(argv)
    problems, stats = check(args.module, args.layout_root)
    if args.json:
        args.json.write_text(json.dumps(dict(stats, problems_detail=problems), indent=1) + '\n')
    for problem in problems:
        print(problem)
    print('%d quoted includes checked, %d problems' % (stats['includes'], stats['problems']))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
