"""Local G2 sampled-field review; no solver, publication or acceptance action."""
import argparse
import csv
from datetime import datetime, timezone
import html
import json
import math
import os
from pathlib import Path

from inputs import load_case, sha256

PDF_SHA = '65ae91e8734d8006f4274c70f548f969ab18ca698d8aad8d3b3384882356349c'
CAPTION = 'FIG.4. (a) LES resolution, (b) mean temperature plot for two grids'
PAPER = 'Sharma, De and Kumar (2023), Numerical Investigation of Supercritical Combustion Dynamics in a Multi-Element LOx-Methane Combustor Using Flamelet-Generated Manifold Approach'
URL = 'https://arxiv.org/abs/2311.15034'


def paper(reference_path, pdf_path):
    reference = json.loads(reference_path.read_text())
    if reference.get('schema') != 'sharma-centerline-reference-v1' or reference.get('pdf_sha256') != PDF_SHA or sha256(pdf_path) != PDF_SHA:
        raise ValueError('Reference/PDF identity differs from the inspected Sharma Figure4b')
    if set(reference['series']) != {'fine', 'finer'}:
        raise ValueError('Reference requires fine and finer series')
    for entry in reference['series'].values():
        points = entry['points']
        if len(points) < 2 or any(len(row) != 2 or not all(math.isfinite(v) for v in row) for row in points):
            raise ValueError('Invalid reference points')
        if any(b[0] <= a[0] for a, b in zip(points, points[1:])):
            raise ValueError('Reference points must preserve increasing pixel columns')
    import pymupdf
    with pymupdf.open(pdf_path) as document:
        page = document[9]
        text = ' '.join(page.get_text().split())
        if CAPTION not in text:
            raise ValueError('Original caption was not found on the inspected page')
        raw = document.extract_image(reference['image_xref'])['image']
    import hashlib
    if hashlib.sha256(raw).hexdigest() != reference['image_sha256']:
        raise ValueError('Original panel bytes differ from the reference extraction')
    return reference, raw


def page(out, summary, panels):
    esc = html.escape
    def image(name, title):
        return f'<a href="{name}.png"><img loading="lazy" src="{name}.png" alt="{esc(title)}"></a>'
    body = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>G2 sampled-field review</title><style>
body{{margin:0;background:#f5f4ef;color:#202923;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1280px;margin:auto;padding:32px 24px 70px}}
h1{{font-size:2rem;line-height:1.2}}h2{{font-size:1.35rem}}section{{background:white;padding:22px;margin:24px 0;border:1px solid #dedfd7;border-radius:8px}}
.pair{{display:grid;grid-template-columns:1.35fr 1fr;gap:22px;align-items:start}}img{{width:100%;height:auto}}a{{color:#006c82}}code{{overflow-wrap:anywhere}}
.warning{{border-left:5px solid #b64d32;padding:15px 20px;background:#fff0e6}}table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;text-align:left;border-bottom:1px solid #ddd}}
@media(max-width:760px){{.pair{{grid-template-columns:1fr}}main{{padding:18px 12px}}section{{padding:14px}}}}
</style><main><p>DIAGNOSTIC RESULTS - SCIENTIFIC ACCEPTANCE NOT ASSIGNED</p><h1>{esc(summary['label'])}: G2 sampled fields</h1>
<p>The reference is Sharma Figure4b: axial time-mean temperature. Our line is at radius {summary['near_axis_radius_m']*1000:g} mm.</p>
<p>Retained case conditions: {esc(json.dumps(summary['case_conditions']))}.</p>
<div class="warning">Our coordinates use x_plot = x_mesh - ({summary['x_origin_m']:g} m). {esc(summary['x_origin_note'])}
Instantaneous fields and running means are separate below. A running mean is not evidence of statistical convergence.
OH means species mass fraction and is not OH* chemiluminescence.</div>
<p>Missing sampled categories: {esc(', '.join(summary['missing_categories']) or 'none')}.</p>
<p>Missing requested times: {esc(json.dumps(summary['missing_requested_times']))}.</p>'''
    for panel in panels:
        name, title = panel['name'], panel['title']
        body += f'<section id="{name}"><h2>{esc(title)}</h2>'
        if name.startswith('axial-'):
            body += '<p><a href="#reference">Reference and original caption</a>. Paper curves keep digitized gaps; no fit or acceptance score is applied.</p>'
            body += '<div class="pair">' + image(name, title) + '<div>' + image('original-figure4b', 'Original Sharma Figure4b')
            body += f'<p>{esc(CAPTION)}</p><p>The crop shows panel(b); the caption describes both panels.</p></div></div>'
        else:
            body += image(name, title) + '<p>Additional retained-field diagnostic. No paper radial curve or OH* image is inferred.</p>'
        body += '</section>'
    body += '<section><h2>Retained sample and run limitations</h2><table><tr><th>Sample</th><th>Time</th><th>Rows</th><th>Interpretation</th></tr>'
    for record in summary['samples']:
        meaning = record.get('averaging', {}).get('status', 'instantaneous')
        body += f"<tr><td>{esc(record['kind']+' / '+record['name'])}</td><td>{record['time_s']:g} s</td><td>{record['rows']}</td><td>{esc(meaning)}</td></tr>"
    body += '</table><ul>' + ''.join(f'<li>{esc(str(item))}</li>' for item in summary['limitations']) + '</ul>'
    body += '<p>Operator runtime identities: ' + esc(json.dumps(summary['run_identity'])) + '</p></section>'
    body += f'''<section id="reference"><h2>Reference and provenance</h2><p>{esc(CAPTION)}</p><p>{esc(PAPER)}. <a href="{URL}">Paper</a>.</p>
<p>The gray experimental band represents flame location, not temperature measurements. It is not digitized as a temperature curve.</p>
<p>Return to: {' | '.join(f'<a href="#{p["name"]}">{esc(p["title"])}</a>' for p in panels if p['name'].startswith('axial-'))}.</p>
<p>PDF SHA256: <code>{PDF_SHA}</code>.</p><p><a href="review.json">Input/source/output hashes and diagnostic metadata</a> | <a href="data/">Consumed sampled CSVs</a></p>
<p>No solver execution, scientific approval, merge or publication occurred in this renderer.</p></section></main></html>'''
    (out / 'index.html').write_text(body, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('case', 'reference', 'pdf', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--run-record', type=Path)
    parser.add_argument('--label')
    parser.add_argument('--time', type=float, action='append')
    parser.add_argument('--x-origin-m', type=float, default=0)
    parser.add_argument('--x-origin-note', default='No paper-origin alignment is assumed; the mesh-to-paper transform remains unqualified.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not math.isfinite(args.x_origin_m) or any(not math.isfinite(t) or t < 0 for t in args.time or []):
        raise ValueError('Offset and requested times must be finite; times must be nonnegative')
    data = load_case(args.case, args.time)
    reference, original = paper(args.reference, args.pdf)
    hashes = {**data['input_hashes'], str(args.reference.resolve()): sha256(args.reference), str(args.pdf.resolve()): sha256(args.pdf)}
    identity = {'status': 'runtime job/source identities not supplied'}
    if args.run_record:
        identity = json.loads(args.run_record.read_text())
        allowed = {'job_id', 'job_ids', 'source_commit', 'solver_source', 'case_source', 'environment_sha256', 'solver_sha256', 'library_sha256', 'note'}
        if not isinstance(identity, dict) or set(identity) - allowed:
            raise ValueError('Run record must contain only documented scientific identity fields')
        hashes[str(args.run_record.resolve())] = sha256(args.run_record)
    plan = {'apply': args.apply, 'case': str(args.case.resolve()), 'output': str(args.out.resolve()),
            'sample_groups': len(data['records']), 'input_hashes': hashes, 'x_origin_m': args.x_origin_m,
            'coordinate_transform': 'x_plot=x_mesh-x_origin_m; paper x unchanged', 'missing_categories': data['missing_categories'],
            'missing_requested_times': data['missing_requested_times']}
    if not args.apply:
        print(json.dumps(plan, indent=2)); return
    if any(sha256(path) != expected for path, expected in hashes.items()):
        raise ValueError('Inputs changed after loading; use a retained snapshot')
    args.out.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR', str((args.out/'matplotlib-cache').resolve()))
    os.environ['MPLBACKEND'] = 'Agg'
    from plots import centerline, radial, maps, style
    style()
    (args.out/'original-figure4b.png').write_bytes(original)
    label = args.label or args.case.name
    panels = centerline(data, reference, args.out, args.x_origin_m, label)
    panels += radial(data, args.out, args.x_origin_m, label)
    panels += maps(data, args.out, args.x_origin_m, label)
    (args.out/'data').mkdir()
    records = []
    for index, record in enumerate(data['records']):
        item = {key: value for key, value in record.items() if key != 'fields'}
        item['rows'] = len(next(iter(record['fields'].values())))
        item['ranges'] = {name: {'min': float(value.min()), 'max': float(value.max())} for name, value in record['fields'].items()}
        records.append(item)
        with (args.out/'data'/f"{index:03d}-{record['kind']}-{record['name']}-{record['time_s']:.9g}.csv").open('w', newline='') as handle:
            writer = csv.writer(handle); writer.writerow(record['fields'])
            writer.writerows(zip(*record['fields'].values()))
    summary = {**plan, 'created_at': datetime.now(timezone.utc).isoformat(), 'label': label,
        'near_axis_radius_m': data['observations']['nearAxisRadius_m'], 'x_origin_note': args.x_origin_note,
        'case_conditions': {'pressure_Pa': data['manifest'].get('pressure'),
            'energy_form': data['manifest'].get('energyForm'), 'bounds_policy': data['manifest'].get('boundsPolicy'),
            'stream_temperature_K': {name: value.get('temperature') for name, value in data['manifest'].get('streams', {}).items()}},
        'samples': records, 'run_identity': identity, 'producer_report': data['report'],
        'limitations': data['manifest'].get('approximations', []) + ['Near-axis sampling is not the exact centerline.',
            'Paper mean and our instantaneous fields are different statistics.', 'No paper RMS or scientific acceptance assigned.'],
        'paper_peaks': {name: value['peak'] for name, value in reference['series'].items()},
        'plot_source_hashes': {path.name: sha256(path) for path in Path(__file__).parent.iterdir() if path.suffix in ('.py', '.md')},
        'physical_validation_passed': False, 'independent_science_approval': False}
    page(args.out, summary, panels)
    summary['output_hashes'] = {str(path.relative_to(args.out)): sha256(path) for path in args.out.rglob('*')
                                if path.is_file() and 'matplotlib-cache' not in path.parts}
    (args.out/'review.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'output': str(args.out.resolve()), 'figures': len(panels), 'sample_groups': len(records), 'scientific_acceptance': False}))


if __name__ == '__main__':
    main()
