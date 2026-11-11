"""Bounded unsteady flamelets and honest coordinate remapping for Sharma 1–2."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
import numpy as np
import cantera as ct


def write(path, value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mechanism',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--plan',action='store_true')
    parser.add_argument('--grid',type=int,default=129)
    args=parser.parse_args()
    config={'pressure_Pa':6e6,'oxidizer_K':85,'fuel_K':288,'grid':args.grid,
            'chi_st_s_inverse':[1e4,3e5,2e6],'duration_s':0.001,
            'progress':'(Y_CO2+Y_CO)/(Y_CO2eq+Y_COeq); pure-stream degeneracy excluded',
            'thermo':'ideal gas','transport':'unity Le','heat_transfer':'adiabatic',
            'unreported_paper_choices':['generator, chi family, time integration, inlet/table enthalpy policy'],
            'mechanism_sha256':hashlib.sha256(args.mechanism.read_bytes()).hexdigest()}
    if args.plan:print(json.dumps(config,indent=2));return
    if args.out.exists():raise ValueError('Output exists; use a new experiment directory')
    args.out.mkdir(parents=True)
    from spitfire import ChemicalMechanismSpec,Flamelet,FlameletSpec
    gas=ct.Solution(str(args.mechanism));mechanism=ChemicalMechanismSpec(cantera_solution=gas)
    fuel=mechanism.stream('TPX',(288,6e6,'CH4:1'))
    oxygen=mechanism.stream('TPX',(85,6e6,'O2:1'))
    index={s:i for i,s in enumerate(gas.species_names)}
    receipt={'config':config,'cantera':ct.__version__,'species':gas.species_names,
             'reactions':gas.n_reactions,'branches':[],'scientific_acceptance':False}
    write(args.out/'receipt.json',receipt)
    all_frames=[];z=None;eq_y=None;eq_t=None
    for chi in config['chi_st_s_inverse']:
        start=time.monotonic();record={'chi_st':chi,'status':'started'}
        receipt['branches'].append(record);write(args.out/'receipt.json',receipt)
        try:
            flame=Flamelet(FlameletSpec(mech_spec=mechanism,fuel_stream=fuel,oxy_stream=oxygen,
                initial_condition='equilibrium',grid_points=args.grid,grid_type='clustered',
                stoich_dissipation_rate=chi,dissipation_rate_form='Peters',heat_transfer='adiabatic',
                include_enthalpy_flux=True,include_variable_cp=True))
            if z is None:
                z=flame.mixfrac_grid
                initial=flame.make_library_from_interior_state(flame.current_interior_state)
                eq_t=np.asarray(initial['temperature'])
                eq_y=np.stack([initial['mass fraction '+s] for s in gas.species_names],axis=-1)
                np.savez_compressed(args.out/'equilibrium-initial.npz',Z=z,T=eq_t,Y=eq_y,species=gas.species_names)
            stop={'reason':None}
            def stopping(t,state,residual,n_steps):
                if time.monotonic()-start>240:
                    stop['reason']='240s branch wall limit';return True
                return False
            try:
                lib=flame.integrate_to_time(config['duration_s'],first_time_step=1e-10,
                    max_time_step=1e-5,transient_tolerance=1e-8,nonlinear_solve_tolerance=1e-10,
                    stop_criteria=stopping,write_log=True,log_rate=100,
                    extra_integrator_args={'maximum_time_step_count':4000})
                times=np.asarray(lib.time_values)
                temperature=np.asarray(lib['temperature'])
                species=np.stack([lib['mass fraction '+s] for s in gas.species_names],axis=-1)
            except Exception as error:
                if not hasattr(error,'states') or not len(error.states):raise
                times=np.asarray(error.times);frames=[flame.make_library_from_interior_state(s) for s in error.states]
                temperature=np.stack([f['temperature'] for f in frames])
                species=np.stack([np.stack([f['mass fraction '+s] for s in gas.species_names],axis=-1) for f in frames])
                stop['reason']='partial integration: '+str(error)
            assert np.isfinite(temperature).all() and np.isfinite(species).all()
            np.savez_compressed(args.out/f'chi-{int(chi)}.npz',Z=z,t=times,T=temperature,Y=species,species=gas.species_names)
            selected=np.unique(np.linspace(0,len(times)-1,min(len(times),300)).astype(int))
            all_frames.append((temperature[selected],species[selected]))
            record.update(status='complete' if times[-1]>=0.999999*config['duration_s'] else 'partial',
                final_time_s=float(times[-1]),frames=len(times),minimum_Y=float(species.min()),
                mass_sum_error=float(abs(species.sum(axis=-1)-1).max()),Tmin=float(temperature.min()),Tmax=float(temperature.max()),stop=stop)
        except Exception as error:
            record.update(status='failed',error=str(error),traceback=traceback.format_exc())
        record['wall_s']=time.monotonic()-start
        write(args.out/'receipt.json',receipt)
    if not all_frames:raise RuntimeError('All flamelet branches failed; failure receipts retained')
    # Map each fixed-Z trajectory. No interpolation across Z until each local column is registered.
    temperatures=np.concatenate([f[0] for f in all_frames],axis=0)
    fractions=np.concatenate([f[1] for f in all_frames],axis=0)
    c_eq=eq_y[:,index['CO2']]+eq_y[:,index['CO']]
    c_raw=fractions[:,:,index['CO2']]+fractions[:,:,index['CO']]
    progress=np.divide(c_raw,c_eq[None,:],out=np.full_like(c_raw,np.nan),where=c_eq[None,:]>1e-12)
    cgrid=np.linspace(0,1,100);t_columns=np.full((len(z),100),np.nan);co2_columns=t_columns.copy()
    ambiguity=[];coverage=[]
    for j in range(1,len(z)-1):
        good=np.isfinite(progress[:,j]);c=progress[good,j];t=temperatures[good,j];co2=fractions[good,j,index['CO2']]
        order=np.argsort(c);c,t,co2=c[order],t[order],co2[order]
        c,first=np.unique(c,return_index=True);t=t[first];co2=co2[first]
        if len(c)<2:continue
        mask=(cgrid>=c.min())&(cgrid<=c.max())
        t_columns[j,mask]=np.interp(cgrid[mask],c,t);co2_columns[j,mask]=np.interp(cgrid[mask],c,co2)
        coverage.append({'Z':float(z[j]),'c_min':float(c.min()),'c_max':float(c.max()),'nodes':len(c)})
        for low in np.linspace(0,0.99,100):
            v=temperatures[(progress[:,j]>=low)&(progress[:,j]<low+0.01),j]
            if len(v)>1:ambiguity.append(float(np.ptp(v)))
    zgrid=np.linspace(0,1,100)
    table_t=np.full((100,100),np.nan);table_co2=table_t.copy()
    for k in range(100):
        for j,zz in enumerate(zgrid):
            hi=np.searchsorted(z,zz)
            if hi==0 or hi==len(z):continue
            lo=hi-1;w=(zz-z[lo])/(z[hi]-z[lo])
            if np.isfinite(t_columns[[lo,hi],k]).all():
                table_t[j,k]=(1-w)*t_columns[lo,k]+w*t_columns[hi,k]
                table_co2[j,k]=(1-w)*co2_columns[lo,k]+w*co2_columns[hi,k]
    slices={}
    for zz in [0.1,0.2,0.4,0.6]:
        j=int(np.argmin(abs(z-zz)))
        slices[str(zz)]={'actual_Z':float(z[j]),'c':cgrid.tolist(),
            'T':[float(v) if np.isfinite(v) else None for v in t_columns[j]],
            'Y_CO2':[float(v) if np.isfinite(v) else None for v in co2_columns[j]]}
    np.savez_compressed(args.out/'manifold.npz',Z=zgrid,c=cgrid,T=table_t,Y_CO2=table_co2,
                        burnt_Z=z,burnt_T=eq_t,burnt_Y=eq_y,species=gas.species_names)
    write(args.out/'slices.json',slices)
    receipt.update(table_coverage_fraction=float(np.isfinite(table_t).mean()),
        max_T_spread_in_c_bins_K=max(ambiguity,default=0),coverage=coverage,
        limitation='First diagnostic map merges different transient paths; branch ambiguity is measured, not accepted. Missing cells remain NaN. Burnt line is the equilibrium initial reference.',
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.is_file() and p.name!='receipt.json'})
    write(args.out/'receipt.json',receipt)
    print(json.dumps({'branches':receipt['branches'],'coverage':receipt['table_coverage_fraction']},indent=2))


if __name__=='__main__':main()
