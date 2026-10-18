"""Read-only export of stable, globally ordered single-front checkpoints."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys


def body(text):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    match = re.search(r'\}\s*(\d+)\s*\((.*?)\)\s*', text, re.S)
    if not match:
        raise ValueError('Invalid OpenFOAM list')
    values = list(map(int, match[2].split()))
    assert len(values) == int(match[1])
    return values


def field(path, count, hashes):
    raw = path.read_bytes()
    hashes[str(path)] = hashlib.sha256(raw).hexdigest()
    text = raw.decode()
    vector = path.name == 'U'
    m = re.search(r'internalField\s+uniform\s+([^;]+);', text)
    if m:
        v = list(map(float, m[1].strip('() ').split()))
        return [v[0]] * count
    m = re.search(r'internalField\s+nonuniform\s+List<\w+>\s+(\d+)\s*\((.*?)\)\s*;', text, re.S)
    if not m:
        raise ValueError('Invalid field: ' + str(path))
    values = list(map(float, m[2].replace('(', ' ').replace(')', ' ').split()))
    assert int(m[1]) == count and len(values) == count * (3 if vector else 1)
    return values[::3] if vector else values


def extract(root, job):
    case = root / 'jobs' / job / 'case'
    meta = json.loads((case / 'case.json').read_text())
    cfg = meta['config']
    assert cfg['cells'] == 4000 and cfg['length_m'] == .002
    mesh = (case / 'system/blockMeshDict').read_text()
    assert '(4000 1 1) simpleGrading (1 1 1)' in mesh
    hashes = {}
    addresses = []
    common = None
    for rank in range(4):
        proc = case / ('processor' + str(rank))
        path = proc / 'constant/polyMesh/cellProcAddressing'
        raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        addresses.append(body(raw.decode()))
        times = {p.name for p in proc.iterdir() if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+', p.name)}
        common = times if common is None else common & times
    assert sorted(i for ids in addresses for i in ids) == list(range(cfg['cells']))
    saved = sorted((t for t in common if float(t) > 0), key=float)
    stable = saved[:-1]
    assert len(stable) >= 3
    selected = sorted(set(stable[-11:] + [min(stable, key=lambda t: abs(float(t)-v)) for v in [.0001, .0002, .0003]]), key=float)
    samples = []
    names = ['T', 'p', 'rho', 'U', 'CH4', 'O2', 'CO2', 'H2O', 'OH', 'Cp']
    for time in selected:
        values = {name: [None] * cfg['cells'] for name in names}
        for rank, ids in enumerate(addresses):
            for name in names:
                path = case / ('processor' + str(rank)) / time / name
                for i, value in zip(ids, field(path, len(ids), hashes)):
                    values[name][i] = value
        samples.append({'time_s': float(time), 'fields': values})
    # A checkpoint selected before the latest write should be immutable.
    for name, digest in hashes.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    runtime = json.loads((root / 'jobs' / job / 'runtime-state.json').read_text())
    return {'job': job, 'case': str(case), 'metadata': meta, 'runtime': runtime,
            'newest_excluded_time': saved[-1], 'samples': samples, 'source_hashes': hashes,
            'binary_sha256': (root / 'jobs' / job / 'solver-product.sha256').read_text().strip()}


if __name__ == '__main__':
    root = Path(sys.argv[1]).resolve()
    print(json.dumps({'observed_at': datetime.datetime.now().astimezone().isoformat(),
                      'jobs': [extract(root, job) for job in sys.argv[2:]]}, separators=(',', ':')))
