"""Read-only status and numerical screening of labelled diagnostic flame pilots."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['root', 'ledger', 'check_script']:
        p.add_argument(name, type=Path)
    a = p.parse_args()
    root = a.root.resolve(strict=True)
    def contained(path):
        path = path.resolve(strict=True)
        path.relative_to(root)
        return path
    ledger, check = contained(a.ledger), contained(a.check_script)
    with ledger.open() as f:
        jobs = list(csv.DictReader(f, delimiter='\t'))
    if not jobs or any(not r['job_id'].isdigit() for r in jobs):
        raise ValueError('Expected nonempty ledger with numeric job IDs')
    raw = subprocess.check_output(['sacct', '-n', '-P', '-j', ','.join(r['job_id'] for r in jobs),
                                   '-o', 'JobIDRaw,State,Elapsed,ExitCode'], text=True)
    states = {v[0]: v[1:4] for line in raw.splitlines() if (v := line.split('|'))[0].isdigit()}
    for row in jobs:
        job = contained(root/'jobs'/row['job_id'])
        row['scheduler'] = states.get(row['job_id'], ['UNKNOWN'])
        row['source'] = (job/'source-revision.txt').read_text().strip() if (job/'source-revision.txt').exists() else None
        row['screen_passed'] = False
        result = job/'result'
        if row['scheduler'][0] != 'COMPLETED':
            continue
        if (result/'model-variant.txt').read_text().strip() != row['variant']:
            raise ValueError('Variant mismatch: '+row['job_id'])
        if abs(float((result/'pressure-Pa.txt').read_text())-float(row['pressure_atm'])*101325) > 1e-5:
            raise ValueError('Pressure mismatch: '+row['job_id'])
        process = subprocess.run([sys.executable, str(check), str(result)], text=True, capture_output=True)
        row['screen_passed'] = process.returncode == 0
        if process.returncode:
            row['screen_failure'] = process.stderr+process.stdout
        else:
            row['screen'] = json.loads(process.stdout)
            row['profile_sha256'] = hashlib.sha256((result/'profile.csv').read_bytes()).hexdigest()
            row['input_sha256_receipt'] = (job/'input-sha256.txt').read_text()
    print(json.dumps(dict(observed_utc=datetime.now(timezone.utc).isoformat(), jobs=jobs), indent=2))


if __name__ == '__main__':
    main()
