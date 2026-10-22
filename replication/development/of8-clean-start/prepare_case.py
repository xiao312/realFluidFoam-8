"""Prepare the clean-start 1-D methane/air case for the OF8 diagnostic.

The mesh, boundary conditions, chemistry and thermo dictionaries come unchanged
from the versioned generator chain this repository already carries:

    replication/development/ideal-baseline/prepare.py apply phi110 OUT smoke
      -> replication/development/premixed-paper/prepare.py            (key phi110-equilibrium)
        -> replication/validation/flames/generate_premixed.py

This script only (a) calls that chain, (b) records which controller-level fields
had to change for the unsteady OF8 startup, and (c) hashes the result so a later
run can be bound to exact inputs. It never edits physics dictionaries: pressure,
temperature, composition, mechanism, transport, tolerances and mesh stay as
generated, and any difference is reported instead of being patched.

Usage:
    python3 -B prepare_case.py --out DIR [--source-commit SHA] [--end-time 1e-7]

Output DIR must not exist. A receipt is written next to it as DIR + '.receipt.json'.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GENERATOR = REPO / 'replication/development/ideal-baseline/prepare.py'

# Controller-level adaptations and the reason each one is unavoidable.
ADAPTATIONS = {
    'application': ('realFluidReactingFoam', 'the generated case names the family application; the OF8 build '
                          'in this trial is realFluidReactingFoam (constant/thermophysicalProperties '
                          'is hePsiThermo/idKineticMixture, which that solver supports)'),
    'endTime': ('1e-7', 'the generated smoke mode stops at 1e-9 s, which is shorter than one '
                        'chemistry report interval; a 100 ns bounded startup is requested instead'),
    'writeInterval': ('2e-8', 'the generated interval of 1e-9 s would write 100 checkpoints of '
                              '8000x58 ASCII fields; 2e-8 s gives five, enough for front motion'),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_dict(path):
    return path.read_text()


def write_adapted(control_dict, adaptations):
    """Return (new text, list of applied changes) without touching other entries."""
    text = control_dict
    applied = []
    for key, (value, reason) in adaptations.items():
        # entries may share a line, so match the key plus its value anywhere and
        # never match the bare "stopAt endTime;" selector
        pattern = re.compile(r'(?<![\w.])' + re.escape(key) + r'\s+([^;\s]+)\s*;')
        found = pattern.search(text)
        if not found:
            raise ValueError('no %s entry in controlDict' % key)
        old = found.group(1)
        if value is None:
            applied.append(dict(key=key, old=old, new=None, reason=reason, change='none'))
            continue
        if old == value:
            applied.append(dict(key=key, old=old, new=value, reason=reason, change='already'))
            continue
        text = text[:found.start()] + '%s %s;' % (key, value) + text[found.end():]
        applied.append(dict(key=key, old=old, new=value, reason=reason, change='adapted'))
    return text, applied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-commit', default='')
    parser.add_argument('--key', default='phi110')
    parser.add_argument('--mode', default='smoke')
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()

    out = args.out.resolve()
    if out.exists():
        raise SystemExit('refusing to reuse existing output %s' % out)
    out.parent.mkdir(parents=True, exist_ok=True)
    plan = dict(out=str(out), generator=str(GENERATOR), key=args.key, mode=args.mode,
                source_commit=args.source_commit or 'unrecorded',
                adaptations={k: dict(value=v[0], reason=v[1]) for k, v in ADAPTATIONS.items()})
    if args.plan:
        print(json.dumps(plan, indent=2))
        return

    sys.stdout.flush()
    subprocess.run([sys.executable, '-B', str(GENERATOR), 'apply', args.key,
                    str(out), args.mode], check=True)

    case = out
    control = case / 'system/controlDict'
    before = sha256(control)
    text, applied = write_adapted(read_dict(control), ADAPTATIONS)
    control.write_text(text)
    after = sha256(control)

    files = {}
    for path in sorted(case.rglob('*')):
        if path.is_file():
            files[str(path.relative_to(case))] = sha256(path)
    receipt = dict(
        schema='of8-clean-start-case-receipt-v1',
        case=str(case),
        source_commit=args.source_commit or 'unrecorded',
        generator=dict(script=str(GENERATOR.relative_to(REPO)), key=args.key, mode=args.mode,
                       command=['python3', '-B', str(GENERATOR.relative_to(REPO)), 'apply',
                                args.key, str(out), args.mode]),
        control_dict=dict(sha256_before=before, sha256_after=after, adaptations=applied),
        physics_untouched_notice=(
            'only controller entries listed in control_dict.adaptations were changed; '
            'constant/*, 0/*, blockMesh, schemes and solution were not edited'),
        files=files,
        file_count=len(files),
        scope=('single-rank ideal-gas startup diagnostic; the generated case is 8-rank '
               'shaped in its naming only and was not modified for rank layout'),
    )
    receipt_path = Path(str(out) + '.receipt.json')
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(case=str(case), files=len(files),
                          control_dict=receipt['control_dict'],
                          receipt=str(receipt_path)), indent=2))


if __name__ == '__main__':
    main()
