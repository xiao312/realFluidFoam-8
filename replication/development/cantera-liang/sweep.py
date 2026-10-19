"""Plan or submit a staged sweep after a pilot passes numerical screening."""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['plan', 'apply'])
    for name in ['root', 'release', 'sdk', 'build', 'inputs', 'ledger']:
        p.add_argument(name, type=Path)
    p.add_argument('stage', type=int, choices=range(1, 6))
    p.add_argument('pilot')
    p.add_argument('--variant', default='full')
    p.add_argument('--pressure-atm', type=float, default=100)
    a = p.parse_args()
    root = a.root.resolve(strict=True)
    for name in ['release', 'sdk', 'build', 'inputs', 'ledger']:
        path = getattr(a, name).resolve(strict=True)
        path.relative_to(root)
        setattr(a, name, path)
    if not a.pilot.isdigit() or not (a.build/'build-passed.txt').is_file():
        raise ValueError('Expected a numeric pilot and a successful build')
    allowed = {'dense-increment', 'bounded-takahashi', 'pressure-chemistry', 'fine-grid', 'smoothed-alpha', 'takahashi-table2', 'takahashi-high-t'}
    if (a.variant != 'full' and (not set(a.variant.split(',')) <= allowed or
            len(set(a.variant.split(','))) != len(a.variant.split(',')))) or not 1 <= a.pressure_atm <= 100:
        raise ValueError('Invalid diagnostic options or pressure')
    plan = json.loads((a.inputs/'plan.json').read_text())
    guesses = {row['phi']: row['guess_phi'] for row in plan}
    phis = sorted(guesses)
    if not phis or len(guesses) != len(plan) or any(not .5 <= phi <= 2 or abs(phi*100-round(phi*100))>1e-8 for phi in phis):
        raise ValueError('Expected unique declared phi values with two decimal places in [0.5,2]')
    for phi in phis:
        (a.inputs/f'phi{round(phi*100):03d}'/'guess.csv').resolve(strict=True).relative_to(root)
    print(json.dumps({'stage': a.stage, 'conditions': phis, 'pilot': a.pilot,
                      'variant': a.variant, 'pressure_atm': a.pressure_atm,
                      'maximum_new_core_hours': 4*len(phis), 'action': a.action}), flush=True)
    if a.action == 'plan':
        return
    pilot = (root/'jobs'/a.pilot/'result').resolve(strict=True)
    pilot.relative_to(root)
    result = subprocess.check_output([sys.executable, str(Path(__file__).with_name('check.py')),
                                      str(pilot)], universal_newlines=True)
    if json.loads(result)['stage'] != a.stage:
        raise ValueError('Pilot stage differs from requested sweep')
    variant = (pilot/'model-variant.txt').read_text().strip() if (pilot/'model-variant.txt').exists() else 'full'
    pressure = float((pilot/'pressure-Pa.txt').read_text())/101325 if (pilot/'pressure-Pa.txt').exists() else 100
    if variant != a.variant or abs(pressure-a.pressure_atm) > 1e-9:
        raise ValueError('Pilot model variant/pressure differs from requested sweep')
    import fcntl
    with a.ledger.open('a+') as ledger:
        fcntl.flock(ledger, fcntl.LOCK_EX)
        ledger.seek(0)
        existing = {(r['stage'], r['phi'], r.get('variant', 'full'), r.get('pressure_atm', 100))
                    for r in map(json.loads, ledger) if r}
        for phi in phis:
            if (a.stage, phi, a.variant, a.pressure_atm) in existing:
                continue
            inputs = a.inputs/f'phi{round(phi*100):03d}'
            script = a.release/'replication/development/cantera-liang/submit.sh'
            args = [str(root), str(a.release), str(a.sdk), str(inputs),
                    str(a.stage), str(a.build), str(phi), a.variant, str(a.pressure_atm)]
            subprocess.run(['bash', str(script), 'plan', *args], check=True)
            output = subprocess.check_output(['bash', str(script), 'apply', *args], universal_newlines=True)
            matches = re.findall(r'^([0-9]+)(?:;[^\n]+)?$', output, re.M)
            if len(matches) != 1:
                raise RuntimeError('Ambiguous submission; inspect scheduler before retry: '+output)
            record = {'job': matches[0], 'stage': a.stage, 'phi': phi,
                      'variant': a.variant, 'pressure_atm': a.pressure_atm,
                      'guess_phi': guesses[phi],
                      'source': (a.release/'SOURCE_REVISION').read_text().strip(),
                      'build_job': a.build.name, 'sdk_job': a.sdk.parent.name,
                      'input_directory': str(inputs), 'qualification_pilot': a.pilot,
                      'submitted_epoch': time.time()}
            ledger.write(json.dumps(record)+'\n')
            ledger.flush()
            print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
