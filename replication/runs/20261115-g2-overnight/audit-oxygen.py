"""Independent scalar SRK audit of S20 exports; no CFD or library mutation.

Usage: python audit-oxygen.py --results DIR --thermo FILE --out FILE
The NASA low-temperature extrapolation remains unqualified. A locally stable
homogeneous solution is not proof of globally stable single-phase equilibrium.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--results', type=Path, required=True)
parser.add_argument('--thermo', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
text = args.thermo.read_text(encoding='utf8')
match = re.search(r'(?m)^\s*"O2"\s*\{', text)
assert match, 'O2 dictionary missing'
start = end = match.end()
depth = 1
while depth:
    depth += (text[end] == '{') - (text[end] == '}')
    end += 1
body = text[start:end-1]
low = list(map(float, re.search(r'\blowCpCoeffs\s+\(([^)]+)\)', body)[1].split()))
high = list(map(float, re.search(r'\bhighCpCoeffs\s+\(([^)]+)\)', body)[1].split()))
mid = float(re.search(r'\bTcommon\s+([^;]+);', body)[1])
c = {k: float(v) for k, v in next(csv.DictReader((args.results/'p5610/srk-coefficients.csv').open())).items()}
W, R, b = c['W_kg_kmol'], c['RR_J_kmol_K'], c['b_m3_kmol']


def state(rho, temperature):
    a = c['coef1']-c['coef2']*math.sqrt(temperature)+c['coef3']*temperature
    da = -c['coef2']/(2*math.sqrt(temperature))+c['coef3']
    d2a = c['coef2']/(4*temperature**1.5)
    coeff = low if temperature < mid else high
    h0 = R/W*(sum(coeff[k]*temperature**(k+1)/(k+1) for k in range(5))+coeff[5])
    cp0 = R/W*sum(coeff[k]*temperature**k for k in range(5))
    hf = R/W*(sum(low[k]*298.15**(k+1)/(k+1) for k in range(5))+low[5])
    v = W/rho
    pressure = R*temperature/(v-b)-a/(v*(v+b))
    energy = h0-R/W*temperature+(temperature*da-a)/(b*W)*math.log1p(b/v)
    cv = cp0-R/W+temperature*d2a/(b*W)*math.log1p(b/v)
    dpdrho = -W/rho**2*(-R*temperature/(v-b)**2+a*(2*v+b)/(v*v*(v+b)**2))
    dpdt = R/(v-b)-da/(v*(v+b))
    cp = cv+temperature*dpdt**2/(rho*rho*dpdrho)
    return dict(p=pressure, e=energy, hs=energy+pressure/rho-hf, cv=cv,
                cp=cp, dpdrho=dpdrho)


summaries = []
hashes = {str(args.thermo): hashlib.sha256(args.thermo.read_bytes()).hexdigest()}
for path in sorted(args.results.glob('*/cold-properties.csv')):
    rows = list(csv.DictReader(path.open()))
    errors = []
    for row in rows:
        t, rho = float(row['T_K']), float(row['rho_kg_m3'])
        s = state(rho, t)
        errors.append(dict(T_K=t, pressureRelative=abs(s['p']/float(row['p_Pa'])-1),
                           hsError=abs(s['hs']-float(row['Hs_J_kg'])),
                           cvError=abs(s['cv']-float(row['Cv_J_kg_K'])),
                           analyticCpRelative=abs(s['cp']/float(row['Cp_J_kg_K'])-1),
                           cpDerivativeRelative=abs(float(row['dHs_dT_J_kg_K'])/float(row['Cp_J_kg_K'])-1)))
    summaries.append(dict(mode=path.parent.name, rows=len(rows),
                          maxPressureRelative=max(v['pressureRelative'] for v in errors),
                          maxHsError_J_kg=max(v['hsError'] for v in errors),
                          maxCvError_J_kg_K=max(v['cvError'] for v in errors),
                          maxAnalyticCpRelative=max(v['analyticCpRelative'] for v in errors),
                          worstCpDerivative=max(errors, key=lambda v: v['cpDerivativeRelative'])))
    hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()

recovery = []
for rho, target in [(327.775166, -233838.211), (351.205912, -236969.3278)]:
    lo, hi = 60., 1000.
    assert state(rho, lo)['e'] < target < state(rho, hi)['e']
    for _ in range(80):
        center = (lo+hi)/2
        if state(rho, center)['e'] < target:
            lo = center
        else:
            hi = center
    t = (lo+hi)/2
    s = state(rho, t)
    recovery.append(dict(rho_kg_m3=rho, target_e_J_kg=target, T_K=t,
                         energyResidual_J_kg=s['e']-target, p_Pa=s['p'],
                         Cv_J_kg_K=s['cv'], isothermalSlope=s['dpdrho'],
                         mechanicallyStableLocal=s['dpdrho'] > 0))
report = dict(sourceJob='128116812', summaries=summaries,
              retainedS18RoundedStateRecovery=recovery, inputSha256=hashes,
              scientificAcceptance=False, CFDsteps=0,
              limitations='S18 inputs rounded from retained console diagnostics. Homogeneous rho/e recovery permits pressure response; it is not phase equilibrium, a CFD restart or a solver correction. Below200K NASA extrapolation remains unqualified. Cp finite difference uses1e-3K and needs step refinement near singularities.')
args.out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k != 'inputSha256'}, indent=2))
