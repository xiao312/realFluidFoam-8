"""Read named sampled-set fields and preserve holes and producer limitations."""
import csv
import hashlib
import io
import json
from pathlib import Path
import re

import numpy as np


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    lines = [line.strip() for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    while lines and lines[0].startswith('#') and ',' not in lines[0]:
        lines.pop(0)
    if not lines:
        raise ValueError(f'Empty CSV: {path}')
    lines[0] = lines[0].lstrip('#').strip()
    rows = list(csv.reader(io.StringIO('\n'.join(lines))))
    names = [name.strip() for name in rows[0]]
    if len(set(names)) != len(names) or not set(names) & {'x', 'y', 'z'}:
        raise ValueError(f'Missing or duplicate coordinate header: {path}')
    if not rows[1:] or any(len(row) != len(names) for row in rows[1:]):
        raise ValueError(f'Empty or ragged sampled CSV: {path}')
    values = np.array([[float(value) for value in row] for row in rows[1:]], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f'Nonfinite sampled value: {path}')
    return {name: values[:, i] for i, name in enumerate(names)}


def merge_samples(paths):
    result = {}
    for path in paths:
        fields = read_csv(path)
        if result and len(next(iter(result.values()))) != len(next(iter(fields.values()))):
            raise ValueError('Split sampled field files have different row counts')
        for name, values in fields.items():
            if name in result and not np.array_equal(values, result[name]):
                raise ValueError(f'Conflicting sampled field or coordinate: {name}')
            result[name] = values
    return result


def image_grid(fields, settings, field):
    """Place exact registered points; no interpolation across missing fluid cells."""
    if not settings or not {'x', 'y', 'z', field} <= fields.keys():
        raise ValueError(f'Image map needs registered grid and x,y,z,{field}')
    nx, ny = settings['axialPoints'], settings['radialPoints']
    if type(nx) is not int or type(ny) is not int or not 2 <= nx <= 801 or not 2 <= ny <= 201:
        raise ValueError('Invalid registered image grid')
    x, y = np.linspace(.0001, .1999, nx), np.linspace(.0001, .0248, ny)
    ix = np.rint((fields['x'] - x[0]) / (x[1] - x[0])).astype(int)
    iy = np.rint((fields['y'] - y[0]) / (y[1] - y[0])).astype(int)
    if ((ix < 0) | (ix >= nx) | (iy < 0) | (iy >= ny)).any():
        raise ValueError('Image points fall outside the registered grid')
    if not (np.allclose(fields['x'], x[ix], atol=1e-8, rtol=0) and
            np.allclose(fields['y'], y[iy], atol=1e-8, rtol=0) and np.allclose(fields['z'], 0, atol=1e-10)):
        raise ValueError('Image point is not on the registered plane/grid')
    if len(set(zip(ix, iy))) != len(ix):
        raise ValueError('Duplicate image coordinates')
    values = np.ma.masked_all((ny, nx), dtype=float)
    values[iy, ix] = fields[field]
    return x, y, values


def averaging(report, time):
    audit = report.get('averaging') or {}
    matched = report.get('time') is not None and abs(report['time'] - time) <= max(1e-14, abs(time) * 1e-8)
    counters = audit.get('fields', {}) if matched else {}
    valid = all(name in counters and counters[name].get('accumulatedTime_s', 0) > 0 and
                counters[name].get('steps', 0) >= 1 for name in ('T', 'OH'))
    return {'status': 'producer-reported counters' if valid else 'averaging counters unverified',
            'fields': counters if valid else {}, 'statistical_convergence_established': False,
            'configured_start_s': audit.get('configuredStartTime_s'),
            'note': 'Counters come from the producer report at this exact output time; this renderer does not repeat the processor audit.'}


def load_case(case, requested):
    case = Path(case)
    manifest_path = case / 'direct-g2-input.json'
    manifest = json.loads(manifest_path.read_text())
    observations = manifest.get('observations')
    if not observations or 'nearAxisRadius_m' not in observations or 'radialPositions_m' not in observations:
        raise ValueError('Case lacks the explicit G2 observation contract')
    hashes = {str(manifest_path.resolve()): sha256(manifest_path)}
    report_path = case / 'direct-g2-result.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    if report_path.exists():
        hashes[str(report_path.resolve())] = sha256(report_path)
    records, missing, missing_times = [], [], {}
    for category, kind, geometry in [('instantaneousProfiles', 'instantaneous', 'line'),
                                     ('timeMeanProfiles', 'mean', 'line'),
                                     ('instantaneousImagePlane', 'instantaneous', 'plane'),
                                     ('timeMeanImagePlane', 'mean', 'plane')]:
        directory = case / 'postProcessing' / category
        folders = []
        if directory.exists():
            folders = [(float(path.name), path) for path in directory.iterdir()
                       if path.is_dir() and re.fullmatch(r'\d+(?:\.\d*)?(?:e[-+]?\d+)?', path.name, re.I)]
        selected = ([max(folders)] if folders else []) if not requested else [
            item for item in folders if any(abs(item[0] - value) <= max(1e-14, abs(value) * 1e-8) for value in requested)]
        if requested:
            missing_times[category] = [value for value in requested if not any(
                abs(item[0] - value) <= max(1e-14, abs(value) * 1e-8) for item in selected)]
        if not selected:
            missing.append(category)
        for time, path in sorted(selected):
            groups = {}
            for file in sorted(path.glob('*.csv')):
                match = re.match(r'(nearAxis|radial\d+|midplane)(?:_|\.|$)', file.name)
                if match:
                    groups.setdefault(match[1], []).append(file)
            for name, paths in groups.items():
                before = {str(file.resolve()): sha256(file) for file in paths}
                fields = merge_samples(paths)
                if before != {str(file.resolve()): sha256(file) for file in paths}:
                    raise ValueError('Sample files changed while reading; use a retained snapshot')
                target = 'TMean' if kind == 'mean' else 'T'
                if target not in fields:
                    raise ValueError(f'{name} lacks {target} at {time}')
                if name.startswith('radial') and int(name[6:]) >= len(observations['radialPositions_m']):
                    raise ValueError(f'Unregistered radial line {name}')
                record = {'kind': kind, 'geometry': geometry, 'name': name, 'time_s': time,
                          'fields': fields, 'paths': [str(file.resolve()) for file in paths]}
                if kind == 'mean':
                    record['averaging'] = averaging(report, time)
                if geometry == 'plane':
                    image_grid(fields, observations.get('imageGrid'), target)
                records.append(record)
                hashes.update(before)
    if not records:
        raise ValueError('No selected G2 sampled CSVs; rendering a result requires actual data')
    return {'manifest': manifest, 'observations': observations, 'report': report,
            'records': records, 'missing_categories': missing, 'missing_requested_times': missing_times, 'input_hashes': hashes}
