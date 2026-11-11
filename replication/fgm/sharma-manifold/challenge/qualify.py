"""Execute production-kernel and cryogenic flamelet controls; retain failures."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mechanism',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--plan',action='store_true');args=parser.parse_args()
    if args.plan:
        print('Warm Cantera/Griffon production parity; finite cryogenic rates; actual 33-node 1-us flamelet.');return
    if args.out.exists():raise ValueError('Refusing existing qualification output')
    args.out.mkdir(parents=True);record={'status':'started','python':sys.version,'scientific_acceptance':False}
    started=time.monotonic()
    try:
        import cantera as ct
        import numpy as np
        import scipy
        import spitfire
        from spitfire import ChemicalMechanismSpec,Flamelet,FlameletSpec
        gas=ct.Solution(str(args.mechanism));mechanism=ChemicalMechanismSpec(cantera_solution=gas)
        extension=Path(sys.modules['spitfire.griffon.griffon'].__file__)
        record.update(cantera=ct.__version__,numpy=np.__version__,scipy=scipy.__version__,
            spitfire_path=spitfire.__file__,griffon_sha256=hashlib.sha256(extension.read_bytes()).hexdigest(),
            mechanism_sha256=hashlib.sha256(args.mechanism.read_bytes()).hexdigest(),species=gas.n_species,reactions=gas.n_reactions)
        controls=[]
        for temperature in [85.,400.,1200.,2500.]:
            gas.TPY=temperature,6e6,{'CH4':.15,'O2':.7,'CO2':.05,'H2O':.1,'OH':1e-9}
            actual=np.empty(gas.n_species)
            # The tested binding is (T,rho,Y,out), despite misleading Cython argument names.
            mechanism.griffon.production_rates(gas.T,gas.density,gas.Y,actual)
            expected=gas.net_production_rates*gas.molecular_weights
            error=float(np.max(abs(actual-expected)/(1+abs(expected))))
            controls.append({'T_K':temperature,'all_finite':bool(np.isfinite(actual).all()),'regularized_max_rate_error':error})
            if not np.isfinite(actual).all():raise ValueError('Nonfinite production control')
            if temperature>=400 and error>1e-7:raise ValueError('Warm production parity failed')
        record['rate_controls']=controls
        flame=Flamelet(FlameletSpec(mech_spec=mechanism,
            fuel_stream=mechanism.stream('TPX',(288,6e6,'CH4:1')),
            oxy_stream=mechanism.stream('TPX',(85,6e6,'O2:1')),initial_condition='equilibrium',
            grid_points=33,grid_type='clustered',stoich_dissipation_rate=2e6,
            dissipation_rate_form='Peters',heat_transfer='adiabatic',include_enthalpy_flux=True,include_variable_cp=True))
        lib=flame.integrate_to_time(1e-6,first_time_step=1e-10,max_time_step=1e-7,
            transient_tolerance=1e-8,extra_integrator_args={'maximum_time_step_count':1000},write_log=True)
        times=np.asarray(lib.time_values);temperature=np.asarray(lib['temperature'])
        fractions=np.stack([lib['mass fraction '+s] for s in gas.species_names],axis=-1)
        assert times[-1]>=1e-6 and len(times)>1 and np.isfinite(temperature).all() and np.isfinite(fractions).all()
        np.savez_compressed(args.out/'smoke.npz',t=times,Z=flame.mixfrac_grid,T=temperature,Y=fractions,species=gas.species_names)
        record.update(status='execution-qualified',final_time_s=float(times[-1]),frames=len(times),
            max_temperature_change_K=float(abs(temperature[-1]-temperature[0]).max()),
            minimum_Y=float(fractions.min()),mass_sum_error=float(abs(fractions.sum(axis=-1)-1).max()),
            limitation='Execution qualification only; no paper agreement, grid convergence or cold-thermo acceptance.')
    except Exception as error:
        record.update(status='failed',error=str(error),traceback=traceback.format_exc())
    record['wall_seconds']=time.monotonic()-started
    (args.out/'qualification.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2,allow_nan=False))
    if record['status']=='failed':raise SystemExit(1)


if __name__=='__main__':main()
