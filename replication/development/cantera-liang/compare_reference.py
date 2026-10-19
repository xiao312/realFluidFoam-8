"""Compare screened curves with digitized paper data without extrapolation."""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path


def compare(results, reference):
    rows = []
    excluded = []
    seen = set()
    for row in results:
        stage, phi = row['stage'], row['phi']
        if (stage, phi) in seen:
            raise ValueError('Ambiguous model curve: duplicate stage/phi')
        seen.add((stage, phi))
        if row.get('pressure_atm', 100) != 100 or not row.get('screen_passed', False):
            raise ValueError('Expected screened 100-atm results')
        points = sorted([r for r in reference if r['stage'] == stage], key=lambda r: r['phi'])
        if stage in (2, 3, 4):
            # Original marker centers differ slightly from their nominal phi.
            matches = [r for r in points if abs(r['phi']-phi) < .001]
            if not matches:
                excluded.append(dict(stage=stage, phi=phi, reason='No paper marker at this operating condition'))
                continue
            if len(matches) != 1:
                raise ValueError('Ambiguous paper marker')
            value = matches[0]['speed_cm_s']
            uncertainty = matches[0]['uncertainty_cm_s']
        else:
            xs = [r['phi'] for r in points]
            if phi < xs[0] or phi > xs[-1]:
                excluded.append(dict(stage=stage, phi=phi, reason='Outside digitized curve; no extrapolation'))
                continue
            i = min(max(bisect.bisect_right(xs, phi), 1), len(xs)-1)
            a, b = points[i-1], points[i]
            fraction = (phi-a['phi'])/(b['phi']-a['phi'])
            value = a['speed_cm_s']+fraction*(b['speed_cm_s']-a['speed_cm_s'])
            uncertainty = max(a['uncertainty_cm_s'], b['uncertainty_cm_s'])
        error = row['speed_cm_s']-value
        # Declared numerical comparison screen, not author model identification.
        limit = max(.05, .01*value)+uncertainty
        rows.append(dict(stage=stage, phi=phi, job=row['job'], computed_cm_s=row['speed_cm_s'],
                         paper_cm_s=value, image_uncertainty_cm_s=uncertainty,
                         error_cm_s=error, error_percent=100*error/value,
                         limit_cm_s=limit, within_screen=abs(error)<=limit))
    stages = {}
    for stage in range(1, 6):
        group = [r for r in rows if r['stage']==stage]
        if group:
            stages[str(stage)] = dict(points=len(group),
                rms_cm_s=math.sqrt(sum(r['error_cm_s']**2 for r in group)/len(group)),
                max_abs_cm_s=max(abs(r['error_cm_s']) for r in group),
                failed_points=sum(not r['within_screen'] for r in group))
    return dict(criteria='abs(error) <= max(0.05 cm/s, 1% reference) + digitization uncertainty',
                rows=rows, excluded=excluded, stages=stages, scientific_acceptance=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('results', type=Path)
    p.add_argument('reference', type=Path)
    a = p.parse_args()
    results = json.loads(a.results.read_text(encoding='utf-8-sig'))
    reference = json.loads(a.reference.read_text(encoding='utf-8-sig'))
    report = compare(results['results'], reference['rows'])
    report['input_sha256'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in (a.results, a.reference)}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
