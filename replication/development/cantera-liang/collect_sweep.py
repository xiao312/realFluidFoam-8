"""Collect the swept Fig. 8(a) operating points without claiming scientific acceptance.

Reads `cases/stage-<n>-phi-<x>/` directories written by `job-sweep.sh`, screens each
completed solve with `check.py`, and emits the `results` list that
`compare_reference.py` consumes. A point that did not complete, failed its screen or
reports a different pressure is retained in `failed`, never silently dropped and never
turned into a comparison row.

    python3 collect_sweep.py RUN OUTPUT.json
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

COMPLETED = re.compile(r'^COMPLETED stage=(\d+) phi=([0-9.]+) speed_cm_s=([0-9.eE+-]+)$', re.M)


def printed_precision_tolerance(value):
    """Half a unit in the last digit of the driver's 6-significant-digit report.

    flame.cpp prints the speed with the default stream precision (6 significant
    digits) while profile.csv carries 17. The two are the same number; comparing
    them with a fixed 1e-9 tolerance instead of the print resolution rejects every
    converged case.
    """
    if value == 0.0:
        return 5e-7
    exponent = math.floor(math.log10(abs(value)))
    return 0.5 * 10.0 ** (exponent - 5) * (1.0 + 1e-9)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


NOT_ATTEMPTED = re.compile(r'^NOT_ATTEMPTED\b')


def classify_unfinished(status):
    """('reason', 'not_attempted'|'failed') for a case with no COMPLETED line."""
    if NOT_ATTEMPTED.match(status) or status == 'MISSING':
        return ('the sweep budget ended before this point ran', 'not_attempted')
    return ('the case started but produced no COMPLETED line (interrupted solve)', 'failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path, nargs='+')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    runs = [r.resolve(strict=True) for r in args.run]
    cases = []
    for run in runs:
        found = sorted((run / 'cases').glob('stage-*-phi-*'))
        if not found:
            raise ValueError('no case directories under %s' % (run / 'cases'))
        cases.extend(found)
    # One operating point must have one directory: a point solved twice is ambiguous.
    keys = [c.name for c in cases]
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        raise ValueError('the same operating point appears in more than one run: %s' % duplicates)

    results, failed, not_attempted, observed = [], [], [], []
    for case in cases:
        match = re.match(r'stage-(\d+)-phi-([0-9.]+)$', case.name)
        stage, phi = int(match.group(1)), float(match.group(2))
        battle_log = case / 'batch.log'
        slurm = ''
        if battle_log.exists():
            found = re.search(r'slurm=(\S+)', battle_log.read_text(errors='replace'))
            slurm = found.group(1) if found else ''
        status = (case / 'status.txt').read_text().strip() if (case / 'status.txt').exists() else 'MISSING'
        log = (case / 'flame.log').read_text(errors='replace') if (case / 'flame.log').exists() else ''
        found = COMPLETED.search(log)
        record = dict(job=slurm, case=case.name, stage=stage, phi=phi, status=status)
        if not found:
            # A point the wall budget never reached is not a failed solve, and a solve that
            # was killed is not a point that was never tried: distinguish them so the
            # evidence does not borrow one number for the other.
            record['reason'], record['outcome'] = classify_unfinished(status)
            if record['outcome'] == 'not_attempted':
                not_attempted.append(record)
            else:
                failed.append(record)
            continue
        log_stage, log_phi, log_speed = int(found.group(1)), float(found.group(2)), float(found.group(3))
        if log_stage != stage or abs(log_phi - phi) > 1e-12:
            record['reason'] = 'flame.log identity does not match the case directory'
            failed.append(record)
            continue
        output = case / 'result'
        pressure_file = output / 'pressure-Pa.txt'
        pressure_atm = float(pressure_file.read_text()) / 101325.0 if pressure_file.exists() else None
        variant = (output / 'model-variant.txt').read_text().strip() if (output / 'model-variant.txt').exists() else ''
        record.update(pressure_atm=pressure_atm, variant=variant, speed_from_log_cm_s=log_speed)
        check = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('check.py')), str(output)],
                               capture_output=True, text=True)
        record['screen_passed'] = check.returncode == 0
        if check.returncode != 0:
            record['reason'] = 'numeric screen failed'
            record['check_output'] = (check.stdout + check.stderr)[-2000:]
            failed.append(record)
            continue
        screen = json.loads(check.stdout)
        if abs(screen['speed_cm_s'] - log_speed) > printed_precision_tolerance(log_speed):
            record['reason'] = 'screened speed differs from the logged speed'
            failed.append(record)
            continue
        if pressure_atm is None or abs(pressure_atm - 100.0) > 1e-9:
            record['reason'] = 'pressure is not 100 atm'
            failed.append(record)
            continue
        record.update(speed_cm_s=screen['speed_cm_s'], points=screen['points'],
                      last_refinement_relative_change=screen['last_refinement_relative_change'],
                      mass_flux_relative_range=screen['mass_flux_relative_range'],
                      maximum_species_sum_error=screen['maximum_species_sum_error'],
                      minimum_mass_fraction=screen['minimum_mass_fraction'],
                      output_sha256={name: sha256(output / name) for name in
                                     ('profile.csv', 'refinement.csv', 'property-checks.csv')
                                     if (output / name).exists()})
        results.append(record)
        observed.append(record)

    results.sort(key=lambda r: (r['stage'], r['phi']))
    document = dict(
        run=[str(r) for r in runs],
        schema='forge-fig8a-sweep-v1',
        results=results,
        failed=failed,
        not_attempted=not_attempted,
        counts=dict(completed=len(results), failed=len(failed),
                    not_attempted=len(not_attempted)),
        notes=['screen_passed is a numerical screen (check.py), not paper agreement',
               'scientific acceptance is not claimed by this collector'],
    )
    args.output.write_text(json.dumps(document, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(counts=document['counts'],
                          stages=sorted({r['stage'] for r in results}))))
    return 0 if results else 1


if __name__ == '__main__':
    sys.exit(main())
