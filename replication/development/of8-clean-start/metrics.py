"""Serial 1-D checks for an OpenFOAM real-fluid reacting startup run.

Reads only saved ASCII fields plus the committed janaf/molWeight inputs, so every
number below is derived from the run's own output. Stdlib only.

Usage:
  python3 -B metrics.py --case DIR [--times t,t,...] --out metrics.json

Checks reported (no verdict is assumed; each carries its measured value):
  mesh/geometry      cell count, dx, length from constant/polyMesh points
  finite             min/max of T, p, rho, he, U
  mass fractions     per-species range, sum error, ideal-gas rho closure
  inversion          residual between stored T and T recovered from he
  conservation       total mass and total sensible energy at each saved time
  front              density-weighted front position and gas-relative motion
"""
import argparse
import json
import math
from pathlib import Path
import re

R_UNIVERSAL = 8314.46261815324  # J/(kmol K), the exact value used by liang checks
TREF = 298.15


def species_table(thermo_text):
    """Return ordered species list and per-species (molWeight, janaf coeffs)."""
    m = re.search(r'\bspecies\s+(\d+)\s*\((.*?)\)\s*;', thermo_text, re.S)
    if not m:
        raise ValueError('no species list in thermo input')
    names = m[2].split()
    if len(names) != int(m[1]):
        raise ValueError('species count mismatch')
    table = {}
    for name in names:
        block = re.search(r'(?m)^' + re.escape(name) + r'\s*\{\s*specie\s*\{(.*?)\n\s*\}\s*\}', thermo_text, re.S)
        if not block:
            raise ValueError('missing species block ' + name)
        body = block[1]
        weight = float(re.search(r'molWeight\s+([0-9.eE+-]+)\s*;', body)[1])
        coeffs = {}
        for band in ('low', 'high'):
            found = re.search(band + r'CpCoeffs\s*\(([^)]*)\)', body)
            values = [float(v) for v in found[1].split()]
            if len(values) != 7:
                raise ValueError('janaf band size ' + name)
            coeffs[band] = values
        tcommon = float(re.search(r'Tcommon\s+([0-9.eE+-]+)\s*;', body)[1])
        # Tlow/Thigh are the declared validity range of the JANAF fit. They are carried so a
        # caller can tell an evaluated state from an extrapolated one (job 125296683 ran a
        # 100 K oxidiser against Tlow = 200 K).
        tlow = float(re.search(r'Tlow\s+([0-9.eE+-]+)\s*;', body)[1])
        thigh = float(re.search(r'Thigh\s+([0-9.eE+-]+)\s*;', body)[1])
        table[name] = dict(weight=weight, coeffs=coeffs, tcommon=tcommon,
                           tlow=tlow, thigh=thigh)
    return names, table


def janaf_h_over_R(coeffs, temperature):
    """Dimensionless enthalpy h/R [K] of a NASA-7 (JANAF) species.

    The stored coefficients `a1..a7` are the standard NASA-7 set, for which
    `h/(R T) = a1 + a2 T/2 + a3 T^2/3 + a4 T^3/4 + a5 T^4/5 + a6/T`, so
    `h/R = T * (that)` = `a1 T + a2 T^2/2 + ... + a6`. The multiplication by T
    is written out here; without it the a6 term is divided by T and the result
    is off by a factor of order T (a defect that a synthetic round-trip test
    cannot see, so `test_metrics.py` also checks a hard-coded absolute value).
    """
    a1, a2, a3, a4, a5, a6, _a7 = coeffs
    t = temperature
    return (a1 * t + a2 * t * t / 2 + a3 * t ** 3 / 3 + a4 * t ** 4 / 4
            + a5 * t ** 5 / 5 + a6)


def janaf_cp_over_R(coeffs, temperature):
    """Dimensionless heat capacity cp/R [1] of a NASA-7 species."""
    a1, a2, a3, a4, a5, _a6, _a7 = coeffs
    t = temperature
    return a1 + a2 * t + a3 * t * t + a4 * t ** 3 + a5 * t ** 4


def sensible_enthalpy_MJ(entry, temperature):
    """Sensible enthalpy per kg (J/kg) for one species relative to TREF."""
    band = 'low' if temperature <= entry['tcommon'] else 'high'
    ref_band = 'low' if TREF <= entry['tcommon'] else 'high'
    h = (janaf_h_over_R(entry['coeffs'][band], temperature)
         - janaf_h_over_R(entry['coeffs'][ref_band], TREF))
    return R_UNIVERSAL / entry['weight'] * h


def read_scalar(path, count):
    text = path.read_text()
    m = re.search(r'internalField\s+uniform\s+([^;]+);', text)
    if m:
        return [float(m[1])] * count
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;', text, re.S)
    if not m:
        raise ValueError('invalid scalar field ' + str(path))
    values = [float(v) for v in m[2].split()]
    if int(m[1]) != count or len(values) != count:
        raise ValueError('size mismatch ' + str(path))
    return values


def read_vector_z(path, count):
    text = path.read_text()
    m = re.search(r'internalField\s+uniform\s+\(([^;]*)\);', text)
    if m:
        return [float(m[1].split()[0])] * count
    m = re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;', text, re.S)
    if not m:
        raise ValueError('invalid vector field ' + str(path))
    body = m[2]
    pairs = re.findall(r'\(([^()]*)\)', body)
    values = [float(p.split()[0]) for p in pairs]
    if len(values) != count:
        raise ValueError('vector size mismatch ' + str(path))
    return values


def block_geometry(case):
    text = (case / 'constant/polyMesh/points').read_text()
    points = [(float(a), float(b), float(c)) for a, b, c in
              re.findall(r'\(([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)', text)]
    if not points:
        raise ValueError('no mesh points')
    xs = sorted({p[0] for p in points})
    return dict(points=len(points), x_min=min(xs), x_max=max(xs),
                unique_x=len(xs), dx=min(b - a for a, b in zip(xs, xs[1:])) if len(xs) > 1 else 0.0)


def invert_temperature(entry_weights, cell, target_h, lo=200.0, hi=4000.0):
    """Bisection on sum Y_i hs_i(T) = target_h (cell: list of (Y, entry))."""
    def h_of(t):
        return sum(y * sensible_enthalpy_MJ(e, t) for y, e in cell)
    f_lo = h_of(lo) - target_h
    f_hi = h_of(hi) - target_h
    if f_lo * f_hi > 0:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if h_of(mid) - target_h > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def read_state(case, time_name, names, table):
    directory = case / time_name
    count = len(read_scalar(directory / 'T', len_table_probe(directory)))
    t = read_scalar(directory / 'T', count)
    p = read_scalar(directory / 'p', count)
    rho = read_scalar(directory / 'rho', count)
    he_path = directory / 'he'
    he = read_scalar(he_path, count) if he_path.exists() else None
    cp_path = directory / 'Cp'
    cp = read_scalar(cp_path, count) if cp_path.exists() else None
    uz = read_vector_z(directory / 'U', count)
    ys = {}
    for name in names:
        path = directory / name
        ys[name] = read_scalar(path, count) if path.exists() else [0.0] * count
    return dict(count=count, T=t, p=p, rho=rho, he=he, cp=cp, Uz=uz, Y=ys)


def len_table_probe(directory):
    text = (directory / 'T').read_text()
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)', text)
    if not m:
        return 1
    return int(m[1])  # only used as a count hint; read_scalar re-validates


def analyse_time(case, time_name, names, table, dx):
    state = read_state(case, time_name, names, table)
    n = state['count']
    mol_weight = 0.0
    sum_error = 0.0
    y_min, y_max = 0.0, 1.0
    rho_ideal = []
    for i in range(n):
        s = 0.0
        inverse_weight = 0.0
        for name in names:
            y = state['Y'][name][i]
            s += y
            if y < y_min:
                y_min = y
            if y > y_max:
                y_max = y
            inverse_weight += y / table[name]['weight']
        sum_error = max(sum_error, abs(s - 1.0))
        cell_weight = 1.0 / inverse_weight
        mol_weight += cell_weight / n
        rho_ideal.append(state['p'][i] * cell_weight / (R_UNIVERSAL * state['T'][i]))
    rho_error = max(abs(state['rho'][i] / rho_ideal[i] - 1.0) for i in range(n))

    # temperature inversion from sensible enthalpy. The solver does not write its
    # energy variable by default here, so when `he` is absent it is recomputed from
    # the stored T and Y with the JANAF table and the source of the number is recorded.
    cells = []
    for i in range(n):
        cells.append([(state['Y'][name][i], table[name]) for name in names])
    energy_source = 'he field'
    if state['he'] is None:
        energy_source = 'janaf(T,Y)'
        state['he'] = [sum(y * sensible_enthalpy_MJ(entry, state['T'][i]) for y, entry in cells[i])
                       for i in range(n)]
    residuals = []
    failures = 0
    for i in range(n):
        recovered = invert_temperature(None, cells[i], state['he'][i])
        if recovered is None:
            failures += 1
            continue
        residuals.append(abs(recovered - state['T'][i]) / state['T'][i])

    cp_error = None
    if state['cp'] is not None:
        cp_error = 0.0
        for i in range(n):
            cp_janaf = sum(state['Y'][name][i] * R_UNIVERSAL / table[name]['weight']
                           * janaf_cp_over_R(table[name]['coeffs'][
                               'low' if state['T'][i] <= table[name]['tcommon'] else 'high'],
                               state['T'][i]) for name in names)
            if abs(cp_janaf) > 0.0:
                cp_error = max(cp_error, abs(state['cp'][i] / cp_janaf - 1.0))

    mass = sum(state['rho']) * dx
    energy = sum(state['rho'][i] * state['he'][i] for i in range(n)) * dx

    # Density-deficit weighted front position (classic premixed duct tracker).
    # The unburned density is the median of the first 5 percent of cells, and the
    # deficit is clipped at zero so a handful of denser-than-unburned cells cannot
    # move the centroid outside the slab.
    edge = max(1, n // 20)
    ordered = sorted(state['rho'][:edge])
    rho_unburned = ordered[len(ordered) // 2]
    deficit = [max(0.0, rho_unburned - state['rho'][i]) for i in range(n)]
    total = sum(deficit)
    if total > 0:
        front = sum((i + 0.5) * dx * deficit[i] for i in range(n)) / total
    else:
        front = None
    gradient = [abs(state['T'][i + 1] - state['T'][i]) for i in range(n - 1)]
    peak_index = max(range(len(gradient)), key=lambda i: gradient[i]) if gradient else 0
    mean_uz = sum(state['Uz']) / n

    return dict(
        time_s=float(time_name),
        cells=n,
        finite=dict(
            T=[min(state['T']), max(state['T'])],
            p=[min(state['p']), max(state['p'])],
            rho=[min(state['rho']), max(state['rho'])],
            he=[min(state['he']), max(state['he'])],
            U_z=[min(state['Uz']), max(state['Uz'])],
            all_finite=all(math.isfinite(v) for v in
                           state['T'] + state['p'] + state['rho'] + state['he'] + state['Uz'])),
        mass_fractions=dict(min=min(y_min, 0.0), max=y_max, sum_error=sum_error,
                            ideal_gas_rho_max_rel_error=rho_error,
                            mean_molar_mass_kg_per_kmol=mol_weight),
        inversion=dict(max_rel_residual=max(residuals) if residuals else None,
                       median_rel_residual=sorted(residuals)[len(residuals) // 2] if residuals else None,
                       failed_cells=failures, energy_source=energy_source),
        thermo_cross_check=dict(max_rel_error_Cp_vs_janaf=cp_error),
        conservation=dict(total_mass_kg_per_m2=mass, total_sensible_energy_J_per_m2=energy),
        front=dict(density_deficit_position_m=front,
                   peak_gradient_index=peak_index,
                   peak_gradient_position_m=(peak_index + 0.5) * dx,
                   peak_gradient_K_per_m=gradient[peak_index] / dx if gradient else None,
                   mean_gas_velocity_m_per_s=mean_uz,
                   unburned_reference_density_kg_m3=rho_unburned),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--times', default='')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()

    case = args.case.resolve(strict=True)
    thermo = (case / 'constant/thermo.inputData_GRI').read_text()
    names, table = species_table(thermo)
    geometry = block_geometry(case)
    if geometry['unique_x'] > 1:
        dx = (geometry['x_max'] - geometry['x_min']) / (geometry['unique_x'] - 1)
    else:
        dx = 0.0
    geometry['dx_from_points'] = dx
    geometry['cells_from_points'] = geometry['unique_x'] - 1
    found = sorted([p.name for p in case.iterdir()
                    if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+', p.name)], key=float)
    wanted = [t for t in args.times.split(',') if t] or found
    results = [analyse_time(case, t, names, table, dx) for t in wanted]

    conservation = []
    if len(results) > 1:
        m0 = results[0]['conservation']['total_mass_kg_per_m2']
        e0 = results[0]['conservation']['total_sensible_energy_J_per_m2']
        for row in results:
            conservation.append(dict(
                time_s=row['time_s'],
                mass_rel_change=row['conservation']['total_mass_kg_per_m2'] / m0 - 1.0,
                sensible_energy_rel_change=row['conservation']['total_sensible_energy_J_per_m2'] / e0 - 1.0,
            ))

    front_motion = []
    if len(results) > 1 and all(r['front']['density_deficit_position_m'] is not None for r in results):
        t0 = results[0]
        for row in results[1:]:
            dt = row['time_s'] - t0['time_s']
            if dt <= 0:
                continue
            front_motion.append(dict(
                from_s=t0['time_s'], to_s=row['time_s'],
                front_displacement_m=row['front']['density_deficit_position_m'] - t0['front']['density_deficit_position_m'],
                gas_displacement_m=t0['front']['mean_gas_velocity_m_per_s'] * dt,
                front_minus_gas_m_per_s=(
                    (row['front']['density_deficit_position_m'] - t0['front']['density_deficit_position_m']) / dt
                    - t0['front']['mean_gas_velocity_m_per_s']),
            ))

    payload = dict(
        case=str(case),
        source_files=dict(thermo='constant/thermo.inputData_GRI', species_count=len(names)),
        geometry=geometry,
        times=results,
        conservation_vs_first=conservation,
        front_motion=front_motion,
        scope='bounded startup diagnostics; no flame-speed, convergence or acceptance claim',
    )
    args.out.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({k: payload[k] for k in ('geometry', 'conservation_vs_first', 'front_motion')}, indent=2))


if __name__ == '__main__':
    main()


def read_energy_field(case, time_name, count):
    """Read the solver's own conserved energy variable HE = thermo.he() [J/kg].

    `createFields.H` declares HE as AUTO_WRITE, so every write carries it. Refusing to
    read it made an earlier note claim the build exposes no energy field and made the
    T -> he -> T inversion look like an independent check. Callers that report an energy
    budget have to compare against this field.
    """
    path = Path(case) / time_name / 'HE'
    if not path.exists():
        raise FileNotFoundError('no solver energy field: ' + str(path))
    return read_scalar(path, count)


def energy_field_residual(case, time_name, count, weights, table, temperature,
                          rel_tol=1e-5):
    """Compare HE with sum_i Y_i hs_i(T) cell by cell.

    Returns the worst relative residual over cells whose table enthalpy is not
    negligible, plus the count of failing cells. A missing or inconsistent HE field is a
    hard failure, not a warning: it means the solver's conserved variable and the
    reported budget disagree.
    """
    he = read_energy_field(case, time_name, count)
    worst, failing = 0.0, 0
    for c in range(count):
        hs = sum(y[c] * sensible_enthalpy_MJ(table[s], temperature[c])
                 for y, s in weights)
        scale = max(abs(v) for v in he)
        if abs(hs) <= 1e-3 * scale:
            continue
        rel = abs(he[c] - hs) / abs(hs)
        worst = max(worst, rel)
        if rel > rel_tol:
            failing += 1
    return dict(cells=count, worst_rel_residual=worst, failing_cells=failing,
                ok=(failing == 0 and worst <= rel_tol))
