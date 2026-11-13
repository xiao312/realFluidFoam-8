"""Independent source-state/ignition checks, not a paper-fit objective."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from lookup_baseline import query


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def model(directory):
    data=np.load(directory/'table.npz');rows=[]
    for i in range(len(data['Z'])):
        c=data['c_min'][i]+data['eta']*(data['c_max'][i]-data['c_min'][i])
        axis,index=np.unique(c,return_index=True);v=data['values'][i]
        rows.append((axis,np.column_stack([v[:,0],v[:,1],v[:,3:]])[index]))
    return data,(data['Z'],rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['baseline','candidate','mechanism','probe','out']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--plan',action='store_true');a=p.parse_args()
    identities={name:{'table_sha256':digest(getattr(a,name)/'physical.tbl'),
                      'npz_sha256':digest(getattr(a,name)/'table.npz')}
                for name in ['baseline','candidate']}
    if a.plan:print(json.dumps(dict(plan=True,tables=identities,out=str(a.out))));return
    import cantera as ct
    a.out.mkdir(parents=True,exist_ok=False)
    gas=ct.Solution(str(a.mechanism));fuel={'CH4':.55,'N2':.45};air={'O2':1,'N2':3.76};pressure=101325.
    gas.TPX=298.,pressure,fuel;hf=gas.enthalpy_mass
    gas.TPX=298.,pressure,air;ha=gas.enthalpy_mass
    zst=1/(1+gas.stoich_air_fuel_ratio(fuel,air,basis='mole'))
    report=dict(schema='maders-source-closure-diagnostic/v1',cantera=ct.__version__,Zst=zst,
        tables=identities,mechanism_sha256=digest(a.mechanism),probe_sha256=digest(a.probe),
        driver_sha256=digest(__file__),states=[],reactors=[],scientific_acceptance=False,
        limitation='Actual C++ replay holds rho fixed; Cantera reactor holds pressure and total specific enthalpy. Neither includes spatial transport.')
    for name in ['baseline','candidate']:
        data,lookup=model(getattr(a,name))
        if not np.array_equal(data['species'],gas.species_names):raise ValueError('Species identities differ')
        weights=data['progress_weights'];h=zst*hf+(1-zst)*ha
        for z in [.10,zst,.16]:
            for c in [0.,1e-5,1e-4,.001,.005,.01,.03,.06,.10,.14,.16]:
                try:v=query(lookup,z,c)
                except ValueError:continue
                gas.TPY=float(v[0]),pressure,v[2:]
                rate_at_tdiag=float((gas.net_production_rates*gas.molecular_weights)@weights)
                gas.HPY=z*hf+(1-z)*ha,pressure,v[2:]
                report['states'].append(dict(table=name,Z=z,C=c,Tdiag_K=float(v[0]),
                    T_at_absolute_h_K=gas.T,rho_kg_m3=gas.density,Sc_table=float(v[1]),
                    Sc_chem_at_Tdiag=rate_at_tdiag,
                    Sc_chem_at_absolute_h=float((gas.net_production_rates*gas.molecular_weights)@weights),
                    max_Y_normalization=float(abs(gas.Y-v[2:]).max())))
        # Fixed input values include cold and hot states; never choose them by paper agreement.
        for c in [.001,.01,.03,.10,.14]:
            v=query(lookup,zst,c);gas.HPY=h,pressure,v[2:]
            initial=dict(C=c,T_K=gas.T,rho_kg_m3=gas.density,h_J_kg=gas.enthalpy_mass)
            reactor=ct.IdealGasConstPressureReactor(gas,energy='on',clone=True)
            network=ct.ReactorNet([reactor]);network.rtol=1e-10;network.atol=1e-18
            network.max_steps=100000;history=[]
            for t in [.001,.005,.02]:
                network.advance(t);phase=reactor.phase
                result=subprocess.run([str(a.probe),str(getattr(a,name)/'physical.tbl'),
                    str(zst),str(c),str(initial['rho_kg_m3']),str(t)],check=True,capture_output=True,text=True)
                replay=json.loads(next(line[len('SOURCE_REPLAY '):] for line in result.stdout.splitlines() if line.startswith('SOURCE_REPLAY ')))
                history.append(dict(time_s=t,C_cantera=float(phase.Y@weights),T_cantera_K=phase.T,
                    cantera_h_error_J_kg=phase.enthalpy_mass-initial['h_J_kg'],table_fixed_rho=replay))
            report['reactors'].append(dict(table=name,initial=initial,history=history))
    (a.out/'diagnostic.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    for name in ['baseline','candidate']:
        row=next(x for x in report['states'] if x['table']==name and x['Z']==zst and x['C']==.001)
        run=next(x for x in report['reactors'] if x['table']==name and x['initial']['C']==.001)
        print('COLD_SOURCE_CHECK '+json.dumps(dict(state=row,history=run['history'])),flush=True)


if __name__=='__main__':main()
