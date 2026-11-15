"""Pure-O2 matched-SRK coexistence diagnostic, not a CFD model change.

Requires numpy. Verify audit-oxygen.py against S20 before interpreting this
report. Equality of SRK residual Gibbs energies gives saturation; volume/energy
lever rules then recover the two rounded retained S18 states. This is pure fluid
only, with the original unqualified low-temperature NASA extrapolation.
"""
import argparse
import ast
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import numpy as np
from numpy.polynomial import Polynomial

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--results', type=Path, required=True)
parser.add_argument('--thermo', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()


def bisect_root(function, lo, hi, xtol):
    """Bracketed bisection; deliberately no external nonlinear solver dependency."""
    flo, fhi = function(lo), function(hi)
    if flo*fhi > 0:
        raise ValueError('Unbracketed scalar root')
    for _ in range(100):
        center = (lo+hi)/2
        value = function(center)
        if hi-lo <= xtol or value == 0:
            return center
        if flo*value <= 0:
            hi, fhi = center,value
        else:
            lo,flo = center,value
    raise ValueError('Scalar root iteration ceiling')

source = Path(__file__).with_name('audit-oxygen.py')
tree = ast.parse(source.read_text(encoding='utf8'))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'state']
assert len(functions) == 1
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), globals())
c = {k:float(v) for k,v in next(csv.DictReader((args.results/'p5610/srk-coefficients.csv').open())).items()}
W, R, b = c['W_kg_kmol'], c['RR_J_kmol_K'], c['b_m3_kmol']
text = args.thermo.read_text(encoding='utf8')
match = re.search(r'(?m)^\s*"O2"\s*\{', text)
assert match
start = end = match.end()
depth = 1
while depth:
    depth += (text[end] == '{')-(text[end] == '}')
    end += 1
body = text[start:end-1]
low = list(map(float,re.search(r'\blowCpCoeffs\s+\(([^)]+)\)',body)[1].split()))
high = list(map(float,re.search(r'\bhighCpCoeffs\s+\(([^)]+)\)',body)[1].split()))
mid = float(re.search(r'\bTcommon\s+([^;]+);',body)[1])


def roots(temperature, pressure):
    attraction = c['coef1']-c['coef2']*math.sqrt(temperature)+c['coef3']*temperature
    A = attraction*pressure/(R*temperature)**2
    B = b*pressure/(R*temperature)
    candidates = np.roots([1., -1., A-B-B*B, -A*B])
    z = sorted(float(v.real) for v in candidates if abs(v.imag)<1e-9 and v.real>B)
    assert len(z) == 3, (temperature,pressure,z)
    gibbs = lambda value: value-1-math.log(value-B)-A/B*math.log1p(B/value)
    return z, gibbs(z[0])-gibbs(z[-1])


def saturation(temperature):
    attraction = c['coef1']-c['coef2']*math.sqrt(temperature)+c['coef3']*temperature
    # Spinodal equation in dimensionless x=v/b avoids badly scaled v powers.
    x = Polynomial([0,1])
    polynomial = R*temperature*b*x*x*(x+1)*(x+1)-attraction*(2*x+1)*(x-1)*(x-1)
    volumes = sorted(float(v.real)*b for v in polynomial.roots() if abs(v.imag)<1e-8 and v.real>1)
    assert len(volumes)==2, (temperature, volumes)
    pressures = sorted(R*temperature/(v-b)-attraction/(v*(v+b)) for v in volumes)
    lo,hi = max(1.,pressures[0]),pressures[1]
    margin = max(1e-3,(hi-lo)*1e-7)
    pressure = bisect_root(lambda p: roots(temperature,p)[1],lo+margin,hi-margin,xtol=1e-7)
    z, residual = roots(temperature,pressure)
    densities = [pressure*W/(value*R*temperature) for value in (z[0],z[-1])]
    liquid,vapor = (state(rho,temperature) for rho in densities)
    return dict(T_K=temperature,p_Pa=pressure,rhoLiquid=densities[0],rhoVapor=densities[1],
                eLiquid=liquid['e'],eVapor=vapor['e'],gibbsResidualOverRT=residual)


def mixture(temperature,rho):
    s = saturation(temperature)
    quality = (1/rho-1/s['rhoLiquid'])/(1/s['rhoVapor']-1/s['rhoLiquid'])
    return dict(**s, vaporMassFraction=quality,
                e_J_kg=(1-quality)*s['eLiquid']+quality*s['eVapor'])


# Recheck scalar reconstruction before using the shared formula in a flash.
checks = []
for path in args.results.glob('*/cold-properties.csv'):
    for row in csv.DictReader(path.open()):
        s = state(float(row['rho_kg_m3']),float(row['T_K']))
        checks.append(abs(s['hs']-float(row['Hs_J_kg'])))
assert len(checks)==3116 and max(checks)<1e-6
controls = []
for rho,energy in [(327.775166,-233838.211),(351.205912,-236969.3278)]:
    grid = []
    for temperature in np.linspace(145.,154.49,191):
        try:
            s = mixture(float(temperature),rho)
        except (AssertionError,ValueError):
            continue
        if 0 <= s['vaporMassFraction'] <= 1:
            grid.append(s)
    brackets = [(a['T_K'],z['T_K']) for a,z in zip(grid,grid[1:]) if (a['e_J_kg']-energy)*(z['e_J_kg']-energy)<=0]
    assert len(brackets)==1, (rho,brackets)
    temperature = bisect_root(lambda t:mixture(t,rho)['e_J_kg']-energy,*brackets[0],xtol=1e-11)
    s = mixture(temperature,rho)
    volume = (1-s['vaporMassFraction'])/s['rhoLiquid']+s['vaporMassFraction']/s['rhoVapor']
    controls.append(dict(**s,targetRho=rho,targetEnergy=energy,
                         energyResidual_J_kg=s['e_J_kg']-energy,volumeResidual=volume-1/rho))
report = dict(sourceJob='128116812',CFDsteps=0, scientificAcceptance=False,
              verification=dict(rows=len(checks),maxHsError_J_kg=max(checks)),controls=controls,
              scope='Pure-O2 scalar matched-SRK coexistence diagnostic only. S18 inputs rounded. No multicomponent flash, solver change or CFD restart. Below200K NASA extrapolation remains unqualified.',
              inputSha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,args.thermo,args.results/'p5610/srk-coefficients.csv']})
args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='inputSha256'},indent=2))
