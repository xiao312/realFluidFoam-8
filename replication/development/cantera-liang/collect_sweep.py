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
import re
import subprocess
import sys
from pathlib import Path

COMPLETED = re.compile(r'^COMPLETED stage=(\d+) phi=([0-9.]+) speed_cm_s=([0-9.eE+-]+)$', re.M)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run = args.run.resolve(strict=True)
    cases = sorted((run / 'cases').glob('stage-*-phi-*'))
    if not cases:
        raise ValueError('no case directories under %s' % (run / 'cases'))

    results, failed, observed = [], [], []
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
            record['reason'] = 'no COMPLETED line in flame.log'
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
        if abs(screen['speed_cm_s'] - log_speed) > 1e-9:
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
        run=str(run),
        schema='forge-fig8a-sweep-v1',
        results=results,
        failed=failed,
        counts=dict(completed=len(results), failed=len(failed)),
        notes=['screen_passed is a numerical screen (check.py), not paper agreement',
               'scientific acceptance is not claimed by this collector'],
    )
    args.output.write_text(json.dumps(document, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(counts=document['counts'],
                          stages=sorted({r['stage'] for r in results}))))
    return 0 if results else 1


if __name__ == '__main__':
    sys.exit(main())
