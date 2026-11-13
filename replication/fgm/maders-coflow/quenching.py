"""Solve a denser physical family and transient extinction; never fit paper curves."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mechanism', type=Path, default=Path(__file__).parent/'inputs/drm19.yaml')
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    chis = [.03, .1, .3, 1., 3., 5., 10., 15., 20., 25., 30., 35., 40., 45., 50., 60., 80., 100.]
    times = [0., 1e-6, 3e-6, 1e-5, 3e-5, .0001, .0003, .001, .003, .01, .03, .1, .2]
    plan = dict(schema='maders-quenching-family/v1', grid_points=201,
                chi_st_s_inverse=chis, transient_times_s=times,
                mechanism_sha256=digest(args.mechanism), driver_sha256=digest(__file__),
                formulation='Spitfire unity-Le, prescribed Peters chi; not resolved counterflow strain',
                CFD=False, numerical_flamelet_continuation=True,
                fit_to_paper=False, scientific_acceptance=False)
    if args.plan:
        print(json.dumps(plan, indent=2)); return
    args.out.mkdir(parents=True, exist_ok=False)
    import numpy as np
    import cantera as ct
    from spitfire import ChemicalMechanismSpec, Flamelet, FlameletSpec
    gas = ct.Solution(str(args.mechanism))
    if (gas.n_species, gas.n_reactions) != (21, 84):
        raise ValueError('Require pinned DRM19 with21species/84reactions')
    mechanism = ChemicalMechanismSpec(cantera_solution=gas)
    fuel = mechanism.stream('TPX', (config['fuel_temperature_K'], config['pressure_Pa'], config['fuel_X']))
    air = mechanism.stream('TPX', (config['oxidizer_temperature_K'], config['pressure_Pa'], config['oxidizer_X']))
    hf, ha = fuel.enthalpy_mass, air.enthalpy_mass
    weights = np.zeros(gas.n_species)
    mw_ref = gas.molecular_weights[gas.species_index('H2O')]
    for name in ['CO2', 'H2O', 'H2']:
        i = gas.species_index(name); weights[i] = mw_ref / gas.molecular_weights[i]
    gas.TP = 298.15, config['pressure_Pa']
    h0 = gas.partial_molar_enthalpies / gas.molecular_weights
    manifest = dict(plan, cantera=ct.__version__, profiles=[], failures=[])
    write(args.out/'manifest.json', manifest)

    def create(chi, seed):
        return Flamelet(FlameletSpec(mech_spec=mechanism, fuel_stream=fuel, oxy_stream=air,
            initial_condition=seed, grid_points=201, grid_type='clustered',
            stoich_dissipation_rate=chi, dissipation_rate_form='Peters',
            heat_transfer='adiabatic', include_variable_cp=True, include_enthalpy_flux=True))

    def save(flame, relative, chi, kind, elapsed, error=None, time_s=None):
        directory = args.out/relative; directory.mkdir()
        state = flame.current_interior_state.copy()
        lib = flame.make_library_from_interior_state(state)
        z = flame.mixfrac_grid
        temp = np.array(lib['temperature'])
        y = np.stack([lib['mass fraction '+name] for name in gas.species_names], axis=-1)
        residual = flame.rhs(0., state).reshape((-1, gas.n_species))
        residual[:, 0] /= 1000.
        omega, rho, cp, herr, zerr = [], [], [], [], []
        for j in range(len(z)):
            gas.TPY = temp[j], config['pressure_Pa'], y[j]
            omega.append(gas.net_production_rates*gas.molecular_weights)
            rho.append(gas.density); cp.append(gas.cp_mass)
            herr.append(gas.enthalpy_mass - z[j]*hf - (1-z[j])*ha)
            zerr.append(gas.mixture_fraction(config['fuel_X'], config['oxidizer_X'], basis='mole')-z[j])
        omega = np.array(omega); cp = np.array(cp)
        finite = bool(np.isfinite(y).all() and np.isfinite(temp).all() and np.isfinite(omega).all())
        if not finite: raise ValueError('Nonfinite physical profile')
        np.savez_compressed(directory/'profile.npz', Z=z, T=temp, Y=y,
            C=y@weights, Sc_kg_m3_s=omega@weights, omega_kg_m3_s=omega,
            rho=rho, cp_J_kg_K=cp, lambda_W_m_K=2.58e-5*cp*(temp/298.)**.69,
            mu_Pa_s=1.67e-8*cp*(temp/298.)**.51, species=gas.species_names,
            progress_weights=weights, molecular_weights_kg_kmol=gas.molecular_weights,
            chi_st_s_inverse=chi)
        row = dict(profile=str(relative/'profile.npz'), sha256=digest(directory/'profile.npz'),
            kind=kind, chi_st_s_inverse=chi, transient_time_s=time_s,
            elapsed_s=elapsed, Tmax_K=float(temp.max()), minimum_raw_Y=float(y.min()),
            maximum_sumY_error=float(abs(y.sum(axis=1)-1).max()),
            max_enthalpy_error_J_kg=float(max(abs(np.array(herr)))),
            max_Bilger_error=float(max(abs(np.array(zerr)))), finite=finite,
            scaled_rhs_max=float(abs(residual).max()), solver_error=error,
            steady_residual_pass=bool(abs(residual).max() <= config['steady_tolerance']),
            diagnostic_Qdot_peak_W_m3=float((-omega@h0).max()),
            source_peak_kg_m3_s=float((omega@weights).max()),
            upstream_clipping='Retained Spitfire numerical policy; raw exported fractions preserved')
        write(directory/'receipt.json', row)
        manifest['profiles'].append(row); write(args.out/'manifest.json', manifest)
        print('PHYSICAL_PROFILE '+json.dumps(row), flush=True)
        return row

    last_burning = None
    for index, chi in enumerate(chis):
        start = time.monotonic(); error = None
        seed = 'equilibrium' if last_burning is None else last_burning[1].copy()
        flame = create(chi, seed)
        try:
            flame.compute_steady_state(tolerance=config['steady_tolerance'], verbose=True,
                newton_args={'max_iterations': 40}, psitc_args={'max_iterations': 100},
                transient_args={'extra_integrator_args': {'maximum_time_step_count': 2000}})
        except Exception as problem:
            error = repr(problem); traceback.print_exc()
            manifest['failures'].append(dict(phase='steady', chi=chi, error=error))
        row = save(flame, Path(f'steady-{index:02d}'), chi, 'steady-attempt', time.monotonic()-start, error)
        if row['Tmax_K'] > 1000 and row['steady_residual_pass'] and error is None:
            last_burning = (chi, flame.current_interior_state.copy())
        elif last_burning is not None:
            break
    if last_burning is None:
        raise RuntimeError('No qualified burning seed; failures retained')
    # Numerical continuation is within the 1D flamelet construction, never CFD reuse.
    quench_chi = max(100., 2*last_burning[0])
    flame = create(quench_chi, last_burning[1])
    manifest['quench_seed_chi'] = last_burning[0]
    manifest['quench_chi'] = quench_chi
    for index, target in enumerate(times):
        start = time.monotonic()
        try:
            if target:
                flame.integrate_to_time(target, first_time_step=1e-8, max_time_step=.0002,
                    transient_tolerance=1e-9, minimum_time_step_count=1,
                    save_first_and_last_only=True,
                    extra_integrator_args={'maximum_time_step_count': 20000})
            row = save(flame, Path(f'quench-{index:02d}'), quench_chi, 'transient-quenching',
                       time.monotonic()-start, time_s=target)
        except Exception as problem:
            manifest['failures'].append(dict(phase='transient', time_s=target, error=repr(problem)))
            write(args.out/'manifest.json', manifest); raise
        if row['Tmax_K'] < 500 and target >= .01: break
    manifest['quenching_reached_cold'] = row['Tmax_K'] < 500
    manifest['automatic_CFD_use'] = False
    write(args.out/'manifest.json', manifest)
    print('QUENCHING_COMPLETE '+json.dumps(dict(profiles=len(manifest['profiles']),
          cold=manifest['quenching_reached_cold'], scientific_acceptance=False)), flush=True)


if __name__ == '__main__':
    main()
