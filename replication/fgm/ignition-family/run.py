"""One fresh seeded physical trajectory; preserve partial time coverage honestly."""
import json
from pathlib import Path
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'direct-flamelet'))
from common import inputs,gas_and_streams,sha256,write_json,failure


def arguments(parser):
    parser.add_argument('--settings',required=True,type=Path)
    parser.add_argument('--chi',required=True,type=float)
    parser.add_argument('--upstream-patch-receipt',type=Path)
    parser.add_argument('--upstream-cold-patch-receipt',type=Path)


def main():
    args,config,receipt=inputs(__doc__,arguments)
    settings=json.loads(args.settings.read_text())
    if settings['schema']!='fresh-seeded-flamelet/v1' or args.chi not in settings['chi_st_cases_s_inverse']:
        raise ValueError('Require the declared two-case seeded experiment')
    for key in ('final_time_s','first_step_s','max_step_s','temporal_tolerance','nonlinear_tolerance',
                'integration_wall_limit_s','checkpoint_wall_s'):
        if type(settings[key]) not in (int,float) or not 0<settings[key]<float('inf'):
            raise ValueError(f'Invalid positive setting: {key}')
    for key in ('grid_points','max_steps','max_export_frames','table_z_points','table_eta_points','checkpoint_steps'):
        if type(settings[key]) is not int or settings[key]<3:
            raise ValueError(f'Invalid integer setting: {key}')
    if not (0<settings['seed']['peak_product_fraction']<1 and 0<settings['seed']['mixture_fraction_half_width']<.2):
        raise ValueError('Invalid compact product-seed specification')
    settings['chi_st_s_inverse']=args.chi
    if args.plan:
        print(json.dumps({'experiment':settings,'fresh_start':True,'physical_time_start_s':0,
            'automatic_table_replacement':False,'rebuild_runtime':False},indent=2));return 0
    started=time.monotonic()
    try:
        import cantera as ct
        import numpy as np
        from spitfire import ChemicalMechanismSpec,Flamelet,FlameletSpec
        from spitfire_identity import runtime_identity
        from transient_monitor import ClippingMonitor
        from transient_export import export_frames
        from initialization import prepare
        from observe import Checkpoints,select_frames
        from analysis import diagnostic
        receipt['spitfire_runtime']=runtime_identity(settings,args.upstream_patch_receipt,args.upstream_cold_patch_receipt)
        gas,streams=gas_and_streams(ct,args,config,receipt)
        mechanism=ChemicalMechanismSpec(cantera_solution=gas)
        fuel=mechanism.stream('TPX',(config['fuel']['temperature_k'],config['pressure_pa'],config['fuel']['mole_fractions']))
        oxidizer=mechanism.stream('TPX',(config['oxidizer']['temperature_k'],config['pressure_pa'],config['oxidizer']['mole_fractions']))
        shared=dict(mech_spec=mechanism,fuel_stream=fuel,oxy_stream=oxidizer,
            stoich_dissipation_rate=args.chi,dissipation_rate_form='Peters',heat_transfer='adiabatic',
            include_enthalpy_flux=True,include_variable_cp=True)
        grid_template=Flamelet(FlameletSpec(**shared,initial_condition='unreacted',
            grid_points=settings['grid_points'],grid_type='clustered'))
        z=grid_template.mixfrac_grid
        temperatures,fractions,alpha,initial=prepare(gas,mechanism,streams,config,settings,z)
        write_json(args.out/'initialization.json',initial)
        np.savez_compressed(args.out/'initial.npz',Z=z,T_K=temperatures,Y=fractions,seed_fraction=alpha,
            species=np.array(gas.species_names),pressure_pa=config['pressure_pa'])
        receipt.update(integration=settings,integration_config_sha256=sha256(args.settings),
            initialization_description=initial['kind'],initialization_checks_passed=initial['initialization_checks_passed'],
            status='fresh_initialization_recorded',source_module_files={p.name:sha256(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md')})
        receipt['models'].update(upstream='Sandia Spitfire',transport='unity-Lewis mixture-fraction flamelet',
            low_temperature_policy='Griffon constant-Cp extension below species Tmin; initial HP states use declared Cantera polynomial extrapolation',
            upstream_negative_state_clipping=True)
        write_json(args.out/'receipt.json',receipt)
        if not initial['initialization_checks_passed']:
            raise ValueError('Fresh initialization checks failed; initial arrays and diagnostics retained')
        state=np.column_stack([temperatures[1:-1],fractions[1:-1,:-1]]).ravel()
        flamelet=Flamelet(FlameletSpec(**shared,grid=z,initial_condition=state))
        monitor=ClippingMonitor(gas)
        observer=Checkpoints(args.out,z,settings,gas.n_species)
        receipt['phase_initialization_wall_s']=time.monotonic()-started
        write_json(args.out/'receipt.json',receipt)
        try:
            with monitor:
                solution=flamelet.integrate_to_time(settings['final_time_s'],
                    first_time_step=settings['first_step_s'],max_time_step=settings['max_step_s'],
                    transient_tolerance=settings['temporal_tolerance'],nonlinear_solve_tolerance=settings['nonlinear_tolerance'],
                    write_log=True,log_rate=100,extra_integrator_args={
                        'maximum_time_step_count':settings['max_steps'],'stop_criteria':observer})
        except Exception as error:
            if hasattr(error,'times') and hasattr(error,'states'):
                np.savez_compressed(args.out/'trajectory-partial.npz',time_s=error.times,interior_state=error.states,Z=z)
            raise
        finally:
            observer.close()
            write_json(args.out/'clipping.json',monitor.summary())
        times=solution.time_values
        temperatures=solution['temperature']
        fractions=np.stack([solution['mass fraction '+name] for name in gas.species_names],axis=2)
        np.savez_compressed(args.out/'trajectory.npz',time_s=times,Z=z,T_K=temperatures,Y=fractions,
            species=np.array(gas.species_names),pressure_pa=config['pressure_pa'])
        complete=bool(times[0]==0 and abs(times[-1]-settings['final_time_s'])<=settings['final_time_s']*1e-10)
        receipt.update(status='physical_trajectory_retained',actual_final_time_s=float(times[-1]),
            requested_time_complete=complete,stopped_by_wall=observer.stopped_by_wall,accepted_steps=len(times)-1)
        write_json(args.out/'receipt.json',receipt)
        if not (np.isfinite(temperatures).all() and np.isfinite(fractions).all()):
            raise ValueError('Nonfinite actual trajectory; raw arrays retained')
        selected=select_frames(times,fractions,gas.species_names,z,initial['stoichiometric_Z'])
        settings['selected_frame_indices']=selected
        export_started=time.monotonic()
        metrics=export_frames(ct,gas,mechanism,streams,config,settings,receipt,args,z,times,temperatures,fractions)
        write_json(args.out/'diagnostics.json',metrics)
        history=diagnostic(gas,z,times,temperatures,fractions,config['pressure_pa'],args.chi,initial['stoichiometric_Z'],selected)
        write_json(args.out/'history.json',history)
        receipt.update(status='transient_exported_not_accepted' if complete else 'partial_transient_exported_not_accepted',
            export_wall_s=time.monotonic()-export_started,elapsed_s=time.monotonic()-started,
            automatic_table_replacement=False,steady_convergence_claimed=False,
            artifacts={p.name:sha256(p) for p in args.out.iterdir() if p.is_file() and p.name!='receipt.json'})
        write_json(args.out/'receipt.json',receipt)
        print(json.dumps({'status':receipt['status'],'actual_final_time_s':float(times[-1]),
            'initial_peak_K':history['initial_peak_K'],'final_peak_K':history['final_peak_K'],
            'frames':len(selected),'scientific_acceptance':False}),flush=True)
        return 0 if complete else 5
    except Exception as error:
        (args.out/'traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
        receipt['failure_traceback_sha256']=sha256(args.out/'traceback.txt')
        failure(args,receipt,error,time.monotonic()-started)
        print(f'FAILED: {type(error).__name__}: {error}',file=sys.stderr,flush=True)
        return 4


if __name__=='__main__':
    raise SystemExit(main())
