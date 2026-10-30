"""Independent fixed-density DOP853 reference for actual-table uniform 0D CFD."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp


def source_slice(path, z):
    """Read only the source block, independently of the solver's source kernel."""
    axes = {}
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            name, *values = line.split()
            if name in ['z', 'c', 'c-min', 'c-max']:
                axes[name] = np.asarray(values, dtype=float)
            if name == 'block' and values == ['Sc']:
                source = np.array([np.fromstring(next(stream), sep=' ') for _ in axes['z']])
                break
        else:
            raise ValueError('Missing physical source block')
    zs, eta = axes['z'], axes['c']
    assert zs[0] <= z <= zs[-1] and source.shape == (len(zs), len(eta))
    j = min(len(zs)-2, max(0, int(np.searchsorted(zs, z, side='right'))-1))
    w = (z-zs[j])/(zs[j+1]-zs[j])
    lo = (1-w)*axes['c-min'][j]+w*axes['c-min'][j+1]
    hi = (1-w)*axes['c-max'][j]+w*axes['c-max'][j+1]
    rates = (1-w)*source[j]+w*source[j+1]
    axis = lo+eta*(hi-lo)
    assert hi > lo and np.all(np.diff(axis) > 0) and np.isfinite(rates).all()
    return axis, rates


def integrate(axis, rates, rho, initial, duration, rtol):
    span = axis[-1]-axis[0]
    outside_trials = 0

    def rhs(_time, state):
        nonlocal outside_trials
        c = float(state[0])
        outside_trials += int(c < axis[0] or c > axis[-1])
        # Endpoint linear continuation is solely for rejected RK stages and
        # locating terminal events. It never clips or accepts an out-of-domain state.
        i = min(len(axis)-2, max(0, int(np.searchsorted(axis, c, side='right'))-1))
        value = rates[i]+(rates[i+1]-rates[i])*(c-axis[i])/(axis[i+1]-axis[i])
        return [value/rho]

    def lower(_time, state): return state[0]-axis[0]
    def upper(_time, state): return axis[-1]-state[0]
    lower.terminal = upper.terminal = True
    lower.direction = upper.direction = -1
    solution = solve_ivp(rhs, (0, duration), [initial], method='DOP853',
                         rtol=rtol, atol=rtol*span*1e-2, max_step=duration/200,
                         dense_output=True, events=(lower, upper))
    accepted = solution.y[0]
    complete = bool(solution.success and solution.status == 0 and solution.t[-1] == duration)
    covered = bool(np.all(accepted >= axis[0]) and np.all(accepted <= axis[-1]))
    record = {'rtol': rtol, 'atol': rtol*span*1e-2, 'success': bool(solution.success),
              'complete': complete, 'acceptedStatesCovered': covered,
              'finalTime_s': float(solution.t[-1]), 'acceptedSteps': len(solution.t)-1,
              'rhsEvaluations': solution.nfev, 'outsideTrialEvaluations': outside_trials,
              'events_s': [v.tolist() for v in solution.t_events], 'message': solution.message}
    return solution, record


def evaluate(table, result_path):
    raw_result = result_path.read_bytes()
    result = json.loads(raw_result)
    case = result['input']
    assert case['kind'] == '0d' and case['velocity'] == 0 and case['startTime'] == 0
    initial = result['initial']
    assert initial['t'] == 0 and initial['mass'] > 0 and initial['volume'] > 0
    states = case['states']
    assert all(s['z'] == states[0]['z'] and s['c'] == states[0]['c'] for s in states)
    with table.open('rb') as stream:
        table_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert table_sha == case['inputHashes']['table'], 'CFD/table identity mismatch'
    rho = initial['mass']/initial['volume']
    axis, rates = source_slice(table, states[0]['z'])
    times = np.array([row['t'] for row in result['energy']])
    observed = np.array([row['cmean'] for row in result['energy']])
    assert len(times) > 1 and np.all(np.diff(times) > 0) and times[-1] <= case['endTime']*(1+1e-8)
    solutions = [integrate(axis, rates, rho, initial['cmean'], case['endTime'], tol) for tol in [1e-9, 1e-11]]
    span = axis[-1]-axis[0]
    usable = all(record['complete'] and record['acceptedStatesCovered'] for _, record in solutions)
    rows, comparison = [], None
    density_drift = max(abs(row['mass']/row['volume']/rho-1) for row in result['energy'])
    final = result['finalProfile']
    uniformity = float((max(row['c'] for row in final)-min(row['c'] for row in final))/span) if final else None
    if usable:
        loose, tight = [sol.sol(times)[0] for sol, _ in solutions]
        self_error = float(np.max(np.abs(tight-loose))/span)
        delta = observed-tight
        comparison = {'referenceRefinementMax_Cspan': self_error, 'referenceRefinementLimit_Cspan': 1e-7,
                      'referenceConverged': self_error <= 1e-7,
                      'CFDMaxError_Cspan': float(np.max(np.abs(delta))/span),
                      'CFDRmsError_Cspan': float(np.sqrt(np.mean(delta**2))/span),
                      'CFDFinalError_Cspan': float(delta[-1]/span)}
        rows = [{'time_s': float(t), 'CFD_C': float(c), 'DOP853_C': float(r), 'difference_C': float(c-r)}
                for t, c, r in zip(times, observed, tight)]
    return {'schema': 'fgm-independent-fixed-density-reference-v1',
            'tableSha256': table_sha, 'CFDResultSha256': hashlib.sha256(raw_result).hexdigest(),
            'source': 'Independent adaptive DOP853; no call to the exact piecewise-linear integrator',
            'density_kg_m3': rho, 'mixtureFraction': states[0]['z'], 'Cspan': float(span),
            'densityRelativeDrift': density_drift, 'finalSpatialSpread_Cspan': uniformity,
            'fixedDensityUniformAssumptionsMet': density_drift <= 1e-7 and uniformity is not None and uniformity <= 1e-8,
            'references': [r for _, r in solutions], 'comparison': comparison, 'trajectory': rows,
            'CFDCaseStatus': result['status'], 'scientificAcceptance': False,
            'interpretation': 'Fixed-density uniform ODE comparison only; does not validate SRK/PR, manifold fidelity, or paper agreement. No CFD acceptance limit is changed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table', type=Path, required=True)
    parser.add_argument('--case-result', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out is None:
        print(json.dumps({'dryRun': True, 'table': str(args.table), 'CFDResult': str(args.case_result),
                          'method': 'DOP853', 'rtol': [1e-9, 1e-11], 'referenceRefinementLimit_Cspan': 1e-7}))
        return
    assert not args.out.exists(), 'Refuse to replace a retained comparison'
    report = evaluate(args.table, args.case_result)
    args.out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'trajectory'}, indent=2))


if __name__ == '__main__':
    main()
