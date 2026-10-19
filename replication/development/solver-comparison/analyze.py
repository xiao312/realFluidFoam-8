"""Compare probe CSV against CVODE; keep source and tolerance effects separate."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def analyze(snapshot, reference, output, assert_cache):
    target = {}
    for row in rows(reference/'cantera-probe.csv'):
        key = (int(row['state']), float(row['interval_s']), row['reactor'])
        target.setdefault(key, {})[row['species']] = row
    result = {'reference': json.loads((reference/'chemistry-states.json').read_text()),
              'source_comparisons': [], 'enthalpy_cache_checks': [], 'sha256': {}}
    result['reference'].pop('states')
    for path in sorted(snapshot.glob('*/chemistry-probe.csv')):
        result['sha256'][str(path.relative_to(snapshot))] = hashlib.sha256(path.read_bytes()).hexdigest()
        groups = {}
        for row in rows(path):
            # A failed ODE process can leave a truncated last row; do not accept it.
            if None in row.values():
                continue
            key = (int(row['state']), float(row['interval_s']))
            groups.setdefault(key, {})[row['species']] = row
        for (state, interval), group in groups.items():
            ref = target[(state, interval, 'openfoam-concentration-cp')]
            if set(group) != set(ref):
                continue
            names = sorted(ref)
            native = np.array([float(group[n]['RR_kg_m3_s']) for n in names])
            cvode = np.array([float(ref[n]['RR_kg_m3_s']) for n in names])
            first = group[names[0]]; reference_first = ref[names[0]]
            result['source_comparisons'].append({
                'case': path.parent.name, 'state': state, 'interval_s': interval,
                'T_K': float(first['T_K']),
                'source_vector_relative_L1': float(abs(native-cvode).sum()/max(abs(cvode).sum(), 1e-100)),
                'CH4_source_relative_difference': float(group['CH4']['RR_kg_m3_s'])/float(ref['CH4']['RR_kg_m3_s'])-1,
                'max_absolute_Y_difference': max(abs(float(group[n]['Y_after'])-float(ref[n]['Y_after'])) for n in names),
                'kappa_ratio': float(first['kappa_W_m_K'])/float(reference_first['kappa_W_m_K']),
                'Cp_ratio': float(first['Cp_J_kg_K'])/float(reference_first['Cp_J_kg_K'])})
    for path in sorted(snapshot.glob('*/enthalpy-cache.csv')):
        data = rows(path)
        frozen = sum(float(r['cached_before_J_kg']) == float(r['cached_after_J_kg']) for r in data)
        errors = [abs(float(r['cached_after_J_kg'])-float(r['expected_after_J_kg'])) for r in data]
        result['enthalpy_cache_checks'].append({'case': path.parent.name, 'samples': len(data),
            'unchanged_samples': frozen, 'max_absolute_error_J_kg': max(errors),
            'min_temperature_increment_K': min(float(r['T_after_K'])-float(r['T_before_K']) for r in data),
            'passes_refresh': max(errors) < .01})
        result['sha256'][str(path.relative_to(snapshot))] = hashlib.sha256(path.read_bytes()).hexdigest()
    output.write_text(json.dumps(result, indent=2)+'\n')
    for case in sorted({r['case'] for r in result['source_comparisons']}):
        for dt in [0, 5e-8]:
            values = [r for r in result['source_comparisons'] if r['case']==case and r['interval_s']==dt]
            if values:
                print(case, dt, 'states', len(values), 'max source L1 %',
                      100*max(r['source_vector_relative_L1'] for r in values),
                      'max |deltaY|', max(r['max_absolute_Y_difference'] for r in values))
    print(json.dumps(result['enthalpy_cache_checks'], indent=2))
    if assert_cache and (not result['enthalpy_cache_checks'] or
                         not all(r['passes_refresh'] for r in result['enthalpy_cache_checks'])):
        raise SystemExit('FAIL: species enthalpy does not refresh after thermo.correct()')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot',type=Path);p.add_argument('reference',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--assert-cache-refresh',action='store_true')
    a=p.parse_args();analyze(a.snapshot,a.reference,a.output,a.assert_cache_refresh)
