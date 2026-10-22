#!/usr/bin/env python3
"""Reduce the frozen-state model probe to a conductivity term table.

Round 4 asked a term-level question: the computed case 4 sits 16.9 % above case 3 while
the digitised paper curve sits 4.6 % *below* its case 1, so before any further sweep the
target has to say what the dense-gas conductivity term does on its own, at states taken
from a solved profile, and what flame-speed step that term implies.

`model_probe.cpp` already reports, at nine frozen states of a solved profile and at 1 and
100 atm, three conductivities for the same composition:

  lambda_mix_srk          Cantera mixture-averaged value at the SRK density (the case-3
                          transport baseline)
  lambda_EH_molar         the full rfElyHanley value (the case-4 model)
  lambda_dense_increment  mix-averaged baseline plus the Ely-Hanley dense increment,
                          lambda_mix + (lambda_EH(dense) - lambda_EH(ideal))

This script turns those columns into ratios and into the flame-speed step each form
predicts, using the *measured* sensitivity d ln S / d ln alpha, derived here from the
stage-3 -> stage-4 solved pair at phi = 0.95 and the pointwise conductivity change of the
attribution diagnostic (0.969). Nothing here chooses a form; the paper does not state
which normalisation it used, so both are reported against the same screen and the report
labels case 4 unresolved.

Usage:
  probe_terms.py --probe model-probe.csv --attribution conductivity-attribution.json \
                 --results results.json --out terms.json [--paper-step -0.046]
"""
import argparse
import csv
import hashlib
import json
import math
import pathlib


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def read_probe(path):
    """Return the probe rows as dicts keyed by column name, numbers as floats."""
    with open(path, newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit('probe CSV is empty: %s' % path)
    out = []
    for row in rows:
        clean = {}
        for key, value in row.items():
            if key is None or value is None:
                continue
            try:
                clean[key] = float(value)
            except ValueError:
                clean[key] = value
        out.append(clean)
    return out


def ratio(numerator, denominator, label):
    if not (denominator > 0):
        raise SystemExit('%s: non-positive denominator %r' % (label, denominator))
    value = numerator / denominator
    if not math.isfinite(value):
        raise SystemExit('%s: non-finite ratio' % label)
    return value


def step_for(ratio_value, sensitivity):
    """Flame-speed step implied by a conductivity ratio at fixed pressure.

    S scales with the thermal diffusivity as S ~ alpha^sensitivity, alpha = lambda/(rho cp),
    and the attribution diagnostic measured that exponent at fixed composition and pressure,
    so a conductivity ratio maps to a speed ratio through the same exponent.
    """
    return math.exp(sensitivity * math.log(ratio_value)) - 1.0


def required_ratio(step, sensitivity):
    """Conductivity ratio the paper's case-4 step would need, at the measured exponent."""
    if step <= -1.0:
        raise SystemExit('paper step cannot be <= -100 %')
    return math.exp(math.log(1.0 + step) / sensitivity)


def derived_sensitivity(attribution, results, phi):
    """d ln S / d ln alpha from the stage-3 -> stage-4 pair at one equivalence ratio.

    The pair changes only the conductivity model, so the ratios of the two solved speeds and
    of the two pointwise conductivities give the exponent directly. Both numbers come from
    retained artefacts; nothing is fitted and nothing is assumed.
    """
    speeds = {row['stage']: row['speed_cm_s'] for row in results['results']
              if abs(row['phi'] - phi) < 1e-9}
    if 3 not in speeds or 4 not in speeds:
        raise SystemExit('no stage-3/stage-4 pair at phi=%g in the sweep results' % phi)
    if not (speeds[3] > 0 and speeds[4] > 0):
        raise SystemExit('non-positive solved speed in the pair')
    median_change = attribution['pointwise']['median_relative_conductivity_change']
    median_alpha = attribution['pointwise'].get('median_alpha_ratio')
    if not median_change > -1.0:
        raise SystemExit('conductivity change is not a fraction')
    if median_alpha is not None and not median_alpha > 0:
        raise SystemExit('alpha ratio is not positive')
    by_lambda = math.log(speeds[4] / speeds[3]) / math.log(1.0 + median_change)
    by_alpha = (math.log(speeds[4] / speeds[3]) / math.log(median_alpha)
                if median_alpha else None)
    if not by_lambda > 0 or (by_alpha is not None and not by_alpha > 0):
        raise SystemExit('derived sensitivity is not positive')
    # The prediction below multiplies a *conductivity* ratio, so the exponent measured
    # against the conductivity ratio is the one used; the alpha-based exponent (which also
    # carries the small rho cp change) is reported next to it so the difference is visible.
    return by_lambda, {'stage3_cm_s': speeds[3], 'stage4_cm_s': speeds[4],
                       'median_relative_conductivity_change': median_change,
                       'median_alpha_ratio': median_alpha,
                       'exponent_by_lambda': by_lambda,
                       'exponent_by_alpha': by_alpha,
                       'phi': phi}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', required=True)
    parser.add_argument('--attribution', required=True)
    parser.add_argument('--results', required=True)
    parser.add_argument('--phi', type=float, default=0.95)
    parser.add_argument('--out', required=True)
    parser.add_argument('--paper-step', type=float, default=-0.046,
                        help='digitised paper case-4 step against paper case 1 (fraction)')
    parser.add_argument('--pressure-atm', type=float, default=100.0)
    args = parser.parse_args()

    attribution = json.load(open(args.attribution))
    results = json.load(open(args.results))
    sensitivity, pair = derived_sensitivity(attribution, results, args.phi)

    rows = read_probe(args.probe)
    needed = ['target_T', 'T', 'p_atm', 'lambda_mix_srk', 'lambda_EH_molar',
              'lambda_dense_increment', 'lambda_mix_ideal']
    for row in rows:
        missing = [key for key in needed if key not in row]
        if missing:
            raise SystemExit('probe CSV lacks columns: %s' % ', '.join(missing))

    table = []
    for row in rows:
        if abs(row['p_atm'] - args.pressure_atm) > 1e-9:
            continue
        base = row['lambda_mix_srk']
        full = ratio(row['lambda_EH_molar'], base, 'full/base at T=%g' % row['T'])
        dense = ratio(row['lambda_dense_increment'], base, 'dense/base at T=%g' % row['T'])
        table.append({
            'T_K': row['T'],
            'p_atm': row['p_atm'],
            'rho_kg_m3': row.get('rho_srk'),
            'lambda_mix_srk_W_mK': base,
            'lambda_EH_full_W_mK': row['lambda_EH_molar'],
            'lambda_EH_dense_increment_W_mK': row['lambda_dense_increment'],
            'lambda_mix_ideal_W_mK': row['lambda_mix_ideal'],
            'ratio_full': full,
            'ratio_dense_increment': dense,
            'predicted_step_full': step_for(full, sensitivity),
            'predicted_step_dense_increment': step_for(dense, sensitivity),
        })
    if not table:
        raise SystemExit('no probe rows at %g atm' % args.pressure_atm)

    def stats(key):
        values = sorted(entry[key] for entry in table)
        mid = values[len(values) // 2] if len(values) % 2 else \
            0.5 * (values[len(values) // 2 - 1] + values[len(values) // 2])
        return {'min': values[0], 'median': mid, 'max': values[-1],
                'ratio_max_over_min': values[-1] / values[0] if values[0] > 0 else None}

    summary = {
        'states_compared': len(table),
        'pressure_atm': args.pressure_atm,
        'sensitivity_dlnS_dlnalpha': sensitivity,
        'sensitivity_source': 'stage-3 -> stage-4 solved pair against the pointwise '
                              'conductivity change of the attribution diagnostic',
        'sensitivity_pair': pair,        'full': stats('ratio_full'),
        'dense_increment': stats('ratio_dense_increment'),
        'predicted_step_full_median': step_for(stats('ratio_full')['median'], sensitivity),
        'predicted_step_dense_increment_median':
            step_for(stats('ratio_dense_increment')['median'], sensitivity),
        'paper_step_case4_vs_case1': args.paper_step,
        'required_ratio_for_paper_step': required_ratio(args.paper_step, sensitivity),
        'difference_between_forms_max': max(
            abs(entry['ratio_full'] - entry['ratio_dense_increment']) for entry in table),
    }

    doc = {
        'kind': 'forge-conductivity-terms-v1',
        'probe_csv_sha256': sha256(args.probe),
        'attribution_sha256': sha256(args.attribution),
        'results_sha256': sha256(args.results),
        'script_sha256': sha256(pathlib.Path(__file__).resolve()),
        'summary': summary,
        'table': table,
    }
    with open(args.out, 'w') as handle:
        json.dump(doc, handle, indent=1, sort_keys=True)
        handle.write('\n')

    # A short markdown fragment so the report can quote the table verbatim.
    lines = []
    lines.append('| T (K) | lambda mix (W/m/K) | full Ely-Hanley | dense increment | full / base | increment / base |')
    lines.append('| --- | --- | --- | --- | --- | --- |')
    for entry in table:
        lines.append('| %.0f | %.5f | %.5f | %.5f | %.4f | %.4f |'
                     % (entry['T_K'], entry['lambda_mix_srk_W_mK'],
                        entry['lambda_EH_full_W_mK'], entry['lambda_EH_dense_increment_W_mK'],
                        entry['ratio_full'], entry['ratio_dense_increment']))
    print('\n'.join(lines))
    print('states=%d median full/base=%.4f dense/base=%.4f max |full-dense|=%.2e'
          % (summary['states_compared'], summary['full']['median'],
             summary['dense_increment']['median'], summary['difference_between_forms_max']))
    print('predicted step full=%+.4f dense=%+.4f paper=%+.4f required ratio=%.4f'
          % (summary['predicted_step_full_median'],
             summary['predicted_step_dense_increment_median'],
             args.paper_step, summary['required_ratio_for_paper_step']))


if __name__ == '__main__':
    main()
