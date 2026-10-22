"""Independent recomputation of the energies that the small OF8 cases must conserve.

`metrics.py` reports what the fields contain. This module recomputes the *expected*
values from the case's own initial state and the committed JANAF table, so a
conservation claim is an absolute comparison rather than a self-comparison of two
solver outputs.

Definitions (declared, not inferred):

  sensible enthalpy per kg of mixture   hs(T,Y) = sum_i Y_i hs_i(T)
  formation enthalpy per kg of mixture  hf(Y)   = sum_i Y_i hf_i,  hf_i = ha_i(Tref)
  absolute enthalpy per kg              ha      = hs + hf
  internal energy per kg                u       = ha - p/rho        (ideal gas)
  total specific energy                 e       = u + |U|^2/2

`hs_i` uses the same JANAF coefficients the solver reads (`constant/
thermo.inputData_GRI`) but is evaluated here with an independent implementation:
`ha_i(T) = R/W * (a1 T + a2 T^2/2 + a3 T^3/3 + a4 T^4/4 + a5 T^5/5 + a6)` and
`hs_i = ha_i - ha_i(Tref)` with `Tref = 298.15 K`. `hf_i` is `ha_i(Tref)`, so the
formation enthalpy that the solver's `sensibleEnthalpy` choice drops from its
energy variable is available explicitly.

`chemistry off` case: composition is frozen and the walls are adiabatic, so
`sum(rho*hs)*V` must stay at its initial value; conduction only redistributes it.
`chemistry on` case: heat release converts formation enthalpy into sensible
enthalpy, so `sum(rho*e)*V` is the conserved quantity, not `sum(rho*hs)*V`.

Usage:
    python3 -B expected_energy.py --case DIR --out DIR/expected-energy.json
"""
import argparse
import json
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import (R_UNIVERSAL, TREF, species_table, read_scalar,  # noqa: E402
                     read_vector_z, sensible_enthalpy_MJ, block_geometry)


def ha_over_R(coeffs, temperature):
    """Absolute (formation-inclusive) enthalpy h/R [K] from NASA-7 coefficients."""
    a1, a2, a3, a4, a5, a6, _a7 = coeffs
    t = temperature
    return (a1 * t + a2 * t * t / 2 + a3 * t ** 3 / 3 + a4 * t ** 4 / 4
            + a5 * t ** 5 / 5 + a6)


def absolute_enthalpy(entry, temperature):
    band = 'low' if temperature <= entry['tcommon'] else 'high'
    return R_UNIVERSAL / entry['weight'] * ha_over_R(entry['coeffs'][band], temperature)


def formation_enthalpy(entry):
    ref_band = 'low' if TREF <= entry['tcommon'] else 'high'
    return R_UNIVERSAL / entry['weight'] * ha_over_R(entry['coeffs'][ref_band], TREF)


def time_dirs(case):
    found = [p.name for p in case.iterdir()
             if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+', p.name)]
    return sorted(found, key=float)


def cell_count(directory):
    text = (directory / 'T').read_text()
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)', text)
    return int(m[1]) if m else 1


def analyse(case, names, table, dx):
    hf = {name: formation_enthalpy(table[name]) for name in names}
    rows = []
    for name in time_dirs(case):
        directory = case / name
        n = cell_count(directory)
        T = read_scalar(directory / 'T', n)
        p = read_scalar(directory / 'p', n)
        rho = read_scalar(directory / 'rho', n)
        he = read_scalar(directory / 'he', n)
        Uz = read_vector_z(directory / 'U', n)
        Y = {}
        for species in names:
            path = directory / species
            Y[species] = read_scalar(path, n) if path.exists() else [0.0] * n

        hs_cells, ha_form_cells, sens, abs_e, total_e = [], [], 0.0, 0.0, 0.0
        inversion = []
        for i in range(n):
            hs = 0.0
            hf_mix = 0.0
            for species in names:
                y = Y[species][i]
                entry = table[species]
                hs += y * sensible_enthalpy_MJ(entry, T[i])
                hf_mix += y * hf[species]
            hs_cells.append(hs)
            ha_form_cells.append(hf_mix)
            sens += rho[i] * he[i] * dx
            abs_e += rho[i] * (he[i] + hf_mix) * dx
            total_e += rho[i] * (he[i] + hf_mix + 0.5 * Uz[i] ** 2 - p[i] / rho[i]) * dx
            if T[i] > 0:
                inversion.append(abs(hs - he[i]) / max(abs(he[i]), 1.0))

        rows.append(dict(
            time_s=float(name),
            cells=n,
            measured=dict(sensible_energy_J_per_m2=sens,
                          absolute_enthalpy_J_per_m2=abs_e,
                          total_energy_J_per_m2=total_e,
                          mass_kg_per_m2=sum(rho) * dx),
            janaf_recomputed=dict(
                sensible_energy_J_per_m2=sum(rho[i] * hs_cells[i] for i in range(n)) * dx,
                formation_offset_J_per_m2=sum(rho[i] * ha_form_cells[i] for i in range(n)) * dx,
            ),
            he_vs_janaf=dict(max_rel_error=max(inversion) if inversion else None,
                             median_rel_error=(sorted(inversion)[len(inversion) // 2]
                                               if inversion else None)),
            temperature_K=[min(T), max(T)],
            pressure_Pa=[min(p), max(p)],
            density_kg_m3=[min(rho), max(rho)],
        ))
    return rows


def expected_from_initial_state(case, names, table, dx):
    """Analytic initial energy from 0/T, 0/p and the declared mass fractions."""
    directory = case / '0'
    n = cell_count(directory)
    T = read_scalar(directory / 'T', n)
    p = read_scalar(directory / 'p', n)
    hf = {name: formation_enthalpy(table[name]) for name in names}
    mass = 0.0
    sens = 0.0
    form = 0.0
    for i in range(n):
        inverse_weight = 0.0
        hs = 0.0
        hf_mix = 0.0
        for species in names:
            path = directory / species
            y = read_scalar(path, n)[i] if path.exists() else 0.0
            entry = table[species]
            inverse_weight += y / entry['weight']
            hs += y * sensible_enthalpy_MJ(entry, T[i])
            hf_mix += y * hf[species]
        weight = 1.0 / inverse_weight
        rho = p[i] * weight / (R_UNIVERSAL * T[i])
        mass += rho * dx
        sens += rho * hs * dx
        form += rho * hf_mix * dx
    return dict(mass_kg_per_m2=mass,
                sensible_energy_J_per_m2=sens,
                formation_offset_J_per_m2=form,
                absolute_enthalpy_J_per_m2=sens + form)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expect', default='sensible',
                        choices=['sensible', 'total'],
                        help='what the case is supposed to conserve')
    args = parser.parse_args()

    case = args.case.resolve(strict=True)
    thermo = (case / 'constant/thermo.inputData_GRI').read_text()
    names, table = species_table(thermo)
    geometry = block_geometry(case)
    dx = (geometry['x_max'] - geometry['x_min']) / max(geometry['unique_x'] - 1, 1)

    expected = expected_from_initial_state(case, names, table, dx)
    rows = analyse(case, names, table, dx)

    conserved_key = ('sensible_energy_J_per_m2' if args.expect == 'sensible'
                     else 'total_energy_J_per_m2')
    drift = []
    for row in rows:
        measured = row['measured'][conserved_key]
        ideal = (expected['sensible_energy_J_per_m2'] if args.expect == 'sensible'
                 else expected['sensible_energy_J_per_m2'] + expected['formation_offset_J_per_m2'])
        drift.append(dict(
            time_s=row['time_s'],
            measured_J_per_m2=measured,
            expected_J_per_m2=ideal,
            relative_to_expected=measured / ideal - 1.0,
            relative_to_first_write=(measured / rows[0]['measured'][conserved_key] - 1.0),
        ))

    payload = dict(
        schema='of8-energy-expected-v1',
        case=str(case),
        declared_conserved_quantity=conserved_key,
        expected_initial_state=expected,
        times=rows,
        conservation=drift,
        scope=('bounded single-rank conservation/inversion diagnostic; recomputation '
               'from the case initial state and the committed JANAF table; no flame, '
               'no flame-speed, no convergence claim'),
    )
    args.out.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps(dict(expected=expected, conservation=drift), indent=2))


if __name__ == '__main__':
    main()
