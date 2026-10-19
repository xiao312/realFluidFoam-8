"""Freeze independent flame states and compare CVODE reactor formulations."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import warnings
import cantera as ct
import numpy as np


def run(profile, mechanism, output):
    output.mkdir(exist_ok=False)
    gas = ct.Solution(str(mechanism))
    with profile.open() as stream:
        rows = list(csv.DictReader(stream))
    indices = [min(range(len(rows)), key=lambda i: abs(float(rows[i]['T_K'])-t))
               for t in [500, 780.8722452267356, 1000, 1200, 1500, 1800, 2100]]
    indices += [max(range(len(rows)), key=lambda i: float(rows[i]['Qdot_W_m3']))]
    states = []
    for i in indices:
        row = rows[i]
        raw = np.array([float(row[n]) for n in gas.species_names])
        ys = np.maximum(raw, 0); ys /= ys.sum()
        states.append({'profile_index': i, 'T': float(row['T_K']), 'p': 10132500,
                       'Y': dict(zip(gas.species_names, ys.tolist())),
                       'clipped_negative_mass_fraction': float(-np.minimum(raw, 0).sum())})
    record = {'cantera_version': ct.__version__, 'profile_sha256': hashlib.sha256(profile.read_bytes()).hexdigest(),
              'mechanism_sha256': hashlib.sha256(mechanism.read_bytes()).hexdigest(), 'states': states}
    (output/'chemistry-states.json').write_text(json.dumps(record, indent=2)+'\n')
    with (output/'cantera-probe.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['state','reactor','interval_s','species','T_initial_K','T_after_K',
                         'rho_initial_kg_m3','Cp_J_kg_K','kappa_W_m_K','Y_initial','RR_kg_m3_s','Y_after'])
        for index, state in enumerate(states):
            for kind in ['constant-pressure-adiabatic', 'constant-volume-isothermal']:
                for dt in [0, 1e-9, 5e-9, 5e-8, 5e-7]:
                    gas.TPY = state['T'], state['p'], state['Y']
                    rho, cp, kappa = gas.density, gas.cp_mass, gas.thermal_conductivity
                    y0 = gas.Y.copy()
                    rates = gas.net_production_rates*gas.molecular_weights
                    if dt:
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore', DeprecationWarning)
                            reactor = (ct.IdealGasConstPressureReactor(gas, clone=True) if kind.startswith('constant-pressure')
                                       else ct.IdealGasReactor(gas, energy='off', clone=True))
                        network = ct.ReactorNet([reactor]); network.rtol = 1e-11; network.atol = 1e-18
                        network.advance(dt)
                        final_y, final_t = reactor.phase.Y, reactor.T
                        # Compare native averaged sources using the same initial density.
                        rates = rho*(final_y-y0)/dt
                    else:
                        final_y, final_t = y0, gas.T
                    for j, name in enumerate(gas.species_names):
                        writer.writerow([index, kind, dt, name, state['T'], final_t, rho, cp,
                                         kappa, y0[j], rates[j], final_y[j]])
    print(json.dumps({'states': len(states), 'cantera_version': ct.__version__, 'output': str(output)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('mechanism',type=Path);p.add_argument('output',type=Path)
    a = p.parse_args();run(a.profile,a.mechanism,a.output)
