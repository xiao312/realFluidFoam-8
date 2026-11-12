"""Physical DRM19 flamelets for a published coflow; no paper-profile fitting."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def solve(config, mechanism_path, out, chi, recover_profile=None):
    import numpy as np
    import cantera as ct
    from spitfire import ChemicalMechanismSpec, Flamelet, FlameletSpec
    started = time.monotonic()
    gas = ct.Solution(str(mechanism_path))
    if gas.n_species != 21 or gas.n_reactions != 84:
        raise ValueError('Expected original DRM19: 21 species and 84 reactions')
    mechanism = ChemicalMechanismSpec(cantera_solution=gas)
    pressure = config['pressure_Pa']
    fuel = mechanism.stream('TPX', (config['fuel_temperature_K'], pressure, config['fuel_X']))
    air = mechanism.stream('TPX', (config['oxidizer_temperature_K'], pressure, config['oxidizer_X']))
    weights = np.zeros(gas.n_species)
    reference_mw = gas.molecular_weights[gas.species_index(config['progress_reference_species'])]
    for species in config['progress_species']:
        k = gas.species_index(species)
        weights[k] = reference_mw / gas.molecular_weights[k]
    flame = Flamelet(FlameletSpec(mech_spec=mechanism, fuel_stream=fuel, oxy_stream=air,
        initial_condition='equilibrium', grid_points=config['grid_points'], grid_type='clustered',
        stoich_dissipation_rate=chi, dissipation_rate_form='Peters',
        heat_transfer='adiabatic', include_variable_cp=True, include_enthalpy_flux=True))
    z = flame.mixfrac_grid
    np.savez_compressed(out / 'initial.npz', Z=z, state=flame.current_interior_state)
    solve_error = None
    if recover_profile is not None:
        raw = np.load(recover_profile)
        if not np.array_equal(raw['Z'], z) or not np.array_equal(raw['species'], gas.species_names):
            raise ValueError('Recovery grid/species differ')
        interior = np.column_stack([raw['T'][1:-1], raw['Y'][1:-1, :-1]]).reshape(-1)
    try:
        if recover_profile is None:
            flame.compute_steady_state(tolerance=config['steady_tolerance'], verbose=True,
            newton_args={'max_iterations': 40}, psitc_args={'max_iterations': 100},
            transient_args={'extra_integrator_args': {'maximum_time_step_count': 1200}})
    except Exception as error:
        solve_error = f'{type(error).__name__}: {error}'
        traceback.print_exc()
    state = flame.current_interior_state.copy() if recover_profile is None else interior.copy()
    lib = flame.make_library_from_interior_state(state)
    temperature = np.asarray(lib['temperature'])
    fractions = np.stack([lib['mass fraction ' + s] for s in gas.species_names], axis=-1)
    residual = flame.rhs(0., state).reshape((-1, gas.n_species))
    scaled = residual.copy()
    scaled[:, 0] /= 1000.
    residual_max = float(np.max(abs(scaled)))
    source = []
    density = []
    enthalpy_error = []
    bilger_error = []
    rate_errors = []
    for j, mixture in enumerate(z):
        # Preserve signed raw fractions in the archive; report Cantera normalization.
        gas.TPY = temperature[j], pressure, fractions[j]
        omega = gas.net_production_rates * gas.molecular_weights
        griffon = np.zeros(gas.n_species)
        mechanism.griffon.production_rates(gas.T, gas.density, gas.Y, griffon)
        rate_errors.append(float(np.max(abs(griffon - omega)) / max(1., np.max(abs(omega)))))
        source.append(omega)
        density.append(gas.density)
        enthalpy_error.append(gas.enthalpy_mass - (mixture * fuel.enthalpy_mass + (1 - mixture) * air.enthalpy_mass))
        bilger_error.append(gas.mixture_fraction(config['fuel_X'], config['oxidizer_X'], basis='mole') - mixture)
    source = np.asarray(source)
    progress = fractions @ weights
    progress_source = source @ weights
    cp, mu, conductivity = [], [], []
    for t, y in zip(temperature, fractions):
        gas.TPY = t, pressure, y
        cp.append(gas.cp_mass)
        conductivity.append(2.58e-5 * gas.cp_mass * (t / 298.) ** .69)
        mu.append(1.67e-8 * gas.cp_mass * (t / 298.) ** .51)
    np.savez_compressed(out / 'profile.npz', Z=z, T=temperature, Y=fractions,
        omega_kg_m3_s=source, rho=density, C=progress, Sc_kg_m3_s=progress_source,
        gamma_kmol_kg=progress/reference_mw, gamma_source_kmol_m3_s=progress_source/reference_mw,
        cp_J_kg_K=cp, mu_Pa_s=mu, lambda_W_m_K=conductivity,
        species=gas.species_names, molecular_weights_kg_kmol=gas.molecular_weights,
        progress_weights=weights, chi_st_s_inverse=chi)
    result = {
        'schema': 'maders-physical-flamelet/v1', 'chi_st_s_inverse': chi,
        'elapsed_s': time.monotonic()-started, 'solver_error': solve_error,
        'grid_points': len(z), 'Tmax_K': float(temperature.max()),
        'minimum_raw_Y': float(fractions.min()), 'max_mass_sum_error': float(abs(fractions.sum(axis=1)-1).max()),
        'max_abs_enthalpy_error_J_kg': float(np.max(np.abs(enthalpy_error))),
        'max_abs_bilger_error': float(np.max(np.abs(bilger_error))),
        'max_peak_scaled_Griffon_Cantera_rate_error': max(rate_errors),
        'scaled_rhs_max': residual_max, 'rhs_scaling': 'T/1000 K; species mass fractions/1',
        'steady_tolerance': config['steady_tolerance'],
        'steady_residual_pass': residual_max <= config['steady_tolerance'],
        'burning': bool(temperature.max() > 1000),
        'finite': bool(np.isfinite(fractions).all() and np.isfinite(source).all() and np.isfinite(temperature).all()),
        'cantera': ct.__version__, 'species_count': gas.n_species, 'reaction_count': gas.n_reactions,
        'progress': 'C=MW_H2O*sum(Yi/MWi), i=CO2,H2O,H2; dimensionless',
        'source': 'Sc=sum(MW_H2O/MWi*omega_i), kg/m3/s; signed',
        'raw_composition_preserved': True, 'cantera_property_normalization': True,
        'upstream_negative_state_clipping': 'Spitfire integration policy retained; this run does not establish strict positivity',
        'scientific_acceptance': False, 'is_2d_coflow': False,
        'mechanism_sha256': sha(mechanism_path), 'profile_sha256': sha(out/'profile.npz'),
        'driver_sha256': sha(__file__),
        'recovery_profile_sha256': sha(recover_profile) if recover_profile else None,
        'recovery_scope': 'Postprocess retained physical states; no new integration' if recover_profile else None
    }
    write(out/'receipt.json', result)
    print('FLAMELET_RESULT '+json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--mechanism', type=Path, default=Path(__file__).parent/'inputs/drm19.yaml')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--chi', type=float)
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--recover-profile', type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    if config.get('schema') != 'maders-coflow/v1':
        raise ValueError('Unknown Maders case schema')
    for key in ['pressure_Pa', 'fuel_temperature_K', 'oxidizer_temperature_K', 'steady_tolerance', 'branch_wall_seconds']:
        value = config[key]
        if not isinstance(value, (float, int)) or not 0 < value < float('inf'):
            raise ValueError('Require finite positive '+key)
    if args.plan:
        print(json.dumps({'config':config, 'mechanism_sha256':sha(args.mechanism),
            'fresh_flamelets':True, 'CFD':False, 'output':str(args.out)}, indent=2))
        return
    args.out.mkdir(parents=True, exist_ok=False)
    if args.chi is not None:
        if not 0 < args.chi < float('inf'):
            raise ValueError('Invalid scalar dissipation')
        solve(config, args.mechanism, args.out, args.chi, args.recover_profile)
        return
    rows=[]
    receipt={'config':config, 'mechanism_sha256':sha(args.mechanism), 'driver_sha256':sha(__file__), 'branches':rows,
        'scientific_acceptance':False, 'scope':'Fresh atmospheric flamelet building blocks, not Maders radial profiles'}
    write(args.out/'receipt.json',receipt)
    for i,chi in enumerate(config['chi_st_s_inverse']):
        directory=args.out/f'chi-{i:02d}'
        command=[sys.executable,'-u',str(Path(__file__).resolve()),'--config',str(args.config.resolve()),
            '--mechanism',str(args.mechanism.resolve()),'--out',str(directory.resolve()),'--chi',str(chi)]
        try:
            with (args.out/f'chi-{i:02d}.log').open('w') as log:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=config['branch_wall_seconds'])
            row={'chi_st_s_inverse':chi,'exit_code':result.returncode,'timed_out':False}
        except subprocess.TimeoutExpired:
            row={'chi_st_s_inverse':chi,'exit_code':None,'timed_out':True}
        if (directory/'receipt.json').exists():
            row['physical_result']=json.loads((directory/'receipt.json').read_text())
        rows.append(row)
        write(args.out/'receipt.json',receipt)
        print('BRANCH_RESULT '+json.dumps(row),flush=True)
    receipt['payload_failures'] = sum(r['exit_code'] != 0 for r in rows)
    write(args.out/'receipt.json', receipt)
    if receipt['payload_failures']:
        raise SystemExit(4)


if __name__=='__main__':
    main()
