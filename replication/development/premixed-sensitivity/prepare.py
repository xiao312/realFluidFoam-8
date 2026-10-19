"""Make isolated, hashed restart segments; donor files are never modified."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_entry(text, key, value):
    text, count = re.subn(r'\b' + re.escape(key) + r'\s+[^;]+;', key + ' ' + str(value) + ';', text)
    if count != 1:
        raise ValueError('Expected exactly one dictionary entry: ' + key)
    return text


def prepare(action, job, key, root=Path('/work')):
    config = json.loads(Path(__file__).with_name('study.json').read_text())
    dt = config['cases'][key]
    root = root.resolve()
    job = job.resolve()
    if root not in job.parents or job.parent != root / 'jobs':
        raise ValueError('Expected job directly inside ROOT/jobs')
    donor = root / 'jobs' / config['donor_job'] / 'case'
    checkpoint = config['checkpoint']
    case = job / 'case'
    if case.exists():
        raise ValueError('Refusing existing case: ' + str(case))
    directories = [Path('constant'), Path('system')]
    for rank in range(config['ranks']):
        directories += [Path(f'processor{rank}/constant'), Path(f'processor{rank}') / checkpoint]
        for field in ['T', 'p', 'U', 'OH', 'CH4', 'O2', 'N2']:
            if not (donor / f'processor{rank}' / checkpoint / field).is_file():
                raise ValueError('Incomplete checkpoint: ' + field)
    sources = []
    for directory in directories:
        path = donor / directory
        if path.is_symlink() or not path.is_dir():
            raise ValueError('Missing directory or symlink: ' + str(path))
        for source in sorted(path.rglob('*')):
            if source.is_symlink() or root not in source.resolve().parents:
                raise ValueError('Unreviewed path: ' + str(source))
            if source.is_file():
                sources.append(source)
    controls = {
        'startFrom': 'startTime', 'startTime': checkpoint,
        'endTime': format(float(checkpoint) + config['duration_s'], '.14g'),
        'deltaT': format(dt, '.12g'), 'adjustTimeStep': 'no',
        'writeControl': 'timeStep', 'writeInterval': round(config['field_interval_s'] / dt),
        'runTimeModifiable': 'no',
    }
    print(json.dumps({'key': key, 'donor': str(donor), 'case': str(case),
                      'controls': controls, 'file_count': len(sources), 'config': config}))
    if action == 'plan':
        return
    original = {}
    for source in sources:
        relative = source.relative_to(donor)
        target = case / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(source)
        shutil.copy2(source, target)
        if digest(source) != before or digest(target) != before:
            raise ValueError('Donor changed while copying: ' + str(source))
        original[str(relative)] = before
    control = case / 'system/controlDict'
    text = re.sub(r'\nfunctions\s*\{.*\}\s*$', '\n', control.read_text(), flags=re.S)
    if re.search(r'\bfunctions\b|#include', text):
        raise ValueError('Unreviewed runtime actions in copied controlDict')
    for entry, value in controls.items():
        text = replace_entry(text, entry, value)
    control.write_text(text)
    diagnostic = case / 'constant/flameSpeedProperties'
    interval = round(config['diagnostic_interval_s'] / dt)
    diagnostic.write_text(replace_entry(diagnostic.read_text(), 'interval', interval))
    record = {'key': key, 'config': config, 'controls': controls,
              'diagnostic_interval_steps': interval, 'original_sha256': original,
              'modified_sha256': {str(p.relative_to(case)): digest(p) for p in [control, diagnostic]}}
    (job / 'case-inputs.json').write_text(json.dumps(record, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply'])
    parser.add_argument('job', type=Path)
    parser.add_argument('key', choices=['dt100', 'dt50', 'dt25'])
    args = parser.parse_args()
    prepare(args.action, args.job, args.key)
