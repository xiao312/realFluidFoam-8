"""Read-only collection of staged Cantera results and numerical screening."""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def contained(path, root):
    path = path.resolve(strict=True)
    path.relative_to(root)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('ledger', type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    ledger = contained(args.ledger, root)
    jobs = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    if not jobs or any(not str(job['job']).isdigit() for job in jobs):
        raise ValueError('Expected a nonempty ledger of numeric Slurm job IDs')
    status = subprocess.check_output(
        ['sacct', '-j', ','.join(str(job['job']) for job in jobs),
         '--format=JobIDRaw,State,Elapsed,ExitCode', '-n', '-X', '-P'],
        universal_newlines=True)
    states = {row.split('|')[0]: row.split('|')[1:4] for row in status.splitlines()}
    results = []
    for job in jobs:
        identifier = str(job['job'])
        job['scheduler'] = states.get(identifier)
        if not job['scheduler'] or job['scheduler'][0] != 'COMPLETED':
            continue
        output = contained(root/'jobs'/identifier/'result', root)
        variant = (output/'model-variant.txt').read_text().strip() if (output/'model-variant.txt').exists() else 'full'
        pressure = float((output/'pressure-Pa.txt').read_text())/101325 if (output/'pressure-Pa.txt').exists() else 100
        if variant != job.get('variant', 'full') or abs(pressure-job.get('pressure_atm', 100)) > 1e-9:
            raise ValueError('Recorded model/pressure differs from job output: '+identifier)
        check = subprocess.run([sys.executable, str(Path(__file__).with_name('check.py')),
                                str(output)], capture_output=True, universal_newlines=True)
        job['screen_passed'] = check.returncode == 0
        if check.returncode:
            job['check_error'] = check.stdout + check.stderr
            continue
        job.update(json.loads(check.stdout))
        job['output_sha256'] = {
            name: hashlib.sha256((output/name).read_bytes()).hexdigest()
            for name in ['profile.csv', 'refinement.csv', 'property-checks.csv']}
        job['callbacks'] = (output/'callbacks.txt').read_text()
        results.append(job)
    print(json.dumps({'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'jobs': jobs, 'results': results}, indent=2))


if __name__ == '__main__':
    main()
