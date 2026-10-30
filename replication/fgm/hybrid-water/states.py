"""Explicit state layout and bounded numerical representation corrections."""
import hashlib
import json
from pathlib import Path

import numpy as np

# State rows: C, T[K], h[J/kg], rho[kg/m3], Sc[kg/m3/s], Qformation[W/m3], Y, omega.
C, T, H, RHO, SC, Q, Y0 = range(7)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8')


class StateModel:
    def __init__(self, gas, settings):
        self.gas, self.settings = gas, settings
        self.ns = gas.n_species
        self.progress = [gas.species_index(n) for n in settings['progress_species']]
        self.other = [i for i in range(self.ns) if i not in self.progress]
        self.ys = slice(Y0,Y0+self.ns)
        self.ws = slice(Y0+self.ns,Y0+2*self.ns)
        self.elements = np.asarray([[gas.n_atoms(i,e)*gas.atomic_weight(e)/gas.molecular_weights[i]
                                     for e in gas.element_names] for i in range(self.ns)])
        gas.TP = 298.15,101325
        self.hf = gas.partial_molar_enthalpies/gas.molecular_weights
        self.interpolation_representation = {'evaluations':0,'max_delta_Y':0.0,'max_element_delta':0.0}

    def corrected(self, original, close_zero=False):
        y = np.asarray(original).copy()
        if y.min() < -self.settings['roundoff_negative_limit'] or y[self.progress].min() < 0:
            raise ValueError('Material/negative progress species in physical state')
        before_c = float(y[self.progress].sum())
        y[y < 0] = 0
        zero_applied = close_zero and 0 < before_c <= self.settings['zero_progress_tail_limit']
        if zero_applied:
            y[self.progress] = 0
        major = self.other[int(np.argmax(y[self.other]))]
        y[major] += 1-float(y.sum())
        delta = y-original
        if y.min() < 0 or np.max(np.abs(delta)) > self.settings['roundoff_change_limit']:
            raise ValueError('Numerical mass representation correction exceeds fixed bounds')
        return y, {'minimum_before': float(np.min(original)), 'maximum_delta_Y': float(np.max(np.abs(delta))),
                   'element_delta_max': float(np.max(np.abs(delta@self.elements))),
                   'original_Cwater': before_c, 'zero_tail_applied': bool(zero_applied),
                   'mass_reservoir_species': self.gas.species_names[major]}

    def current(self, gas=None):
        gas = self.gas if gas is None else gas
        y = gas.Y.copy()
        omega = gas.net_production_rates*gas.molecular_weights
        row = np.r_[y[self.progress].sum(),gas.T,gas.enthalpy_mass,gas.density,
                    omega[self.progress].sum(),-self.hf@omega,y,omega]
        if not np.isfinite(row).all():
            raise ValueError('Nonfinite physical state or chemistry')
        return row

    def at_ty(self, temperature, y, close_zero=False):
        corrected, audit = self.corrected(y,close_zero)
        self.gas.TPY = temperature,self.settings['pressure_pa'],corrected
        row = self.current()
        audit['normalization_delta_Y'] = float(np.max(np.abs(row[self.ys]-corrected)))
        # Enthalpy is linear in Y at fixed T; this audit does not evaluate rates on negative species.
        species_h = self.gas.partial_molar_enthalpies/self.gas.molecular_weights
        audit['enthalpy_delta_J_kg'] = float(species_h@(row[self.ys]-y))
        return row,audit

    def at_hy(self, enthalpy, y):
        corrected,audit = self.corrected(y)
        self.interpolation_representation['evaluations'] += 1
        self.interpolation_representation['max_delta_Y'] = max(self.interpolation_representation['max_delta_Y'],audit['maximum_delta_Y'])
        self.interpolation_representation['max_element_delta'] = max(self.interpolation_representation['max_element_delta'],audit['element_delta_max'])
        self.gas.HPY = enthalpy,self.settings['pressure_pa'],corrected
        row = self.current()
        if abs(row[H]-enthalpy) > max(abs(enthalpy),abs(self.gas.cp_mass*self.gas.T),1)*1e-8:
            raise ValueError('Interpolated HP inversion failed')
        return row,audit
