"""PR-VTA postprocessing with explicit mixture-critical and minor-species policies."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import cantera as ct
import numpy as np
from ruamel.yaml import YAML

R = ct.gas_constant  # J/(kmol K); volumes m3/kmol and molecular weights kg/kmol


def parameters(gas):
    database = Path(ct.get_data_directories()[-1]) / 'critical-properties.yaml'
    source = YAML(typ='safe').load(database)
    records = {s['name'].upper(): s['critical-parameters'] for s in source['species']}
    result = []
    # Retained realFluidFoam input data; explicit units K, Pa, m3/kmol.
    stable = {'O2':(154.58,5.043e6,0.073529,0.025),
              'H2O':(647.0,22.064e6,0.055866,0.344),
              'CH4':(190.6,4.61e6,0.0986,0.011),
              'CO2':(304.18,7.38e6,0.0919,0.239),
              'N2':(126.19,3.398e6,0.089445,0.039)}
    for species in gas.species():
        p = records.get(species.name.upper())
        if species.name in stable:
            tc,pc,vc,omega=stable[species.name]
            origin='retained property-thermo.inputData; explicit stable-species parameters'
        elif p and 'critical-molar-volume' in p:
            tc, pc, vc = (p[k] for k in ['critical-temperature', 'critical-pressure', 'critical-molar-volume'])
            omega = p.get('acentric-factor', 0.0)
            origin = 'Cantera critical-properties.yaml'
        else:
            tr = species.transport
            if tr is None:
                raise ValueError('Missing critical and Lennard-Jones data: '+species.name)
            tc = 1.316 * tr.well_depth / ct.boltzmann
            pc = 0.1279 * tr.well_depth / tr.diameter**3
            vc = ct.avogadro * tr.diameter**3 / 0.316
            omega = 0.0
            origin = 'Lennard-Jones corresponding-states estimate; not author critical data'
        result.append({'species':species.name,'Tc':tc,'Pc':pc,'Vc':vc,'omega':omega,
                       'Zc':pc*vc/(R*tc),'origin':origin})
    return result, hashlib.sha256(database.read_bytes()).hexdigest()


def density(temperature, pressure, x, mw, param, critical_rule='eos-equivalent'):
    tc=np.array([p['Tc'] for p in param]);pc=np.array([p['Pc'] for p in param])
    omega=np.array([p['omega'] for p in param]);zc=np.array([p['Zc'] for p in param])
    ai0=0.45724*R*R*tc*tc/pc
    k=0.37464+1.54226*omega-0.26992*omega*omega
    ai=ai0*(1+k*(1-np.sqrt(temperature/tc)))**2
    a=float(np.dot(x,np.sqrt(ai))**2);b=float(np.dot(x,0.07780*R*tc/pc))
    A=a*pressure/(R*temperature)**2;B=b*pressure/(R*temperature)
    roots=np.roots([1,-(1-B),A-3*B*B-2*B,-(A*B-B*B-B**3)])
    real=[float(z.real) for z in roots if abs(z.imag)<1e-9 and z.real>B]
    if not real:raise ValueError('PR has no admissible volume root')
    def residual_g(z):
        return z-1-np.log(z-B)-A/(2*np.sqrt(2)*B)*np.log((z+(1+np.sqrt(2))*B)/(z+(1-np.sqrt(2))*B))
    z=min(real,key=residual_g);v=z*R*temperature/pressure
    dpdv=-R*temperature/(v-b)**2+a*(2*v+2*b)/(v*v+2*b*v-b*b)**2
    if dpdv>=0:raise ValueError('Mechanically unstable selected PR root')
    if critical_rule=='kay':
        tm=float(x@tc);pm=float(x@pc)
    else:
        a0=float(np.dot(x,np.sqrt(ai0))**2)
        tm=0.07780*a0/(0.45724*R*b);pm=0.07780*R*tm/b
    zm=float(x@zc);c1=float(x@(0.4266*zc-0.1101))
    d=-v*v/(R*tm)*dpdv
    c=R*tm/pm*(c1-(0.004+c1)*np.exp(-2*d))
    delta=R*tm/pm*(0.3074-zm)
    translated=v+c+delta*0.35/(0.35+d)
    if translated<=0:raise ValueError('Nonpositive translated volume')
    reconstructed=R*temperature/(v-b)-a/(v*v+2*b*v-b*b)
    return float(x@mw/v),float(x@mw/translated),abs(reconstructed-pressure)/pressure


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--mechanism',default='gri30.yaml')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not args.apply:
        print(json.dumps({'profile':str(args.profile),'out':str(args.out),'writes':False}));return
    if args.out.exists():raise ValueError('Choose a new output directory')
    gas=ct.Solution(args.mechanism);param,digest=parameters(gas)
    raw=list(csv.DictReader(args.profile.open()))
    output=[];minimum_y=0.0;negative_entries=0
    for row in raw:
        y=np.array([float(row['Y_'+s]) for s in gas.species_names])
        # Preserve the approximate input's signed trace values; TPY would silently clip them.
        # This bound limits diagnostic evaluation, not scientific acceptance of negative species.
        if y.min() < -1e-8 or abs(y.sum()-1)>1e-10:raise ValueError('Materially invalid retained fractions')
        minimum_y=min(minimum_y,float(y.min()));negative_entries+=int((y<0).sum())
        x=y/gas.molecular_weights;x=x/x.sum()
        temperature=float(row['T']);pressure=5610000
        pr,vta,error=density(temperature,pressure,x,gas.molecular_weights,param)
        _,kay,_=density(temperature,pressure,x,gas.molecular_weights,param,'kay')
        ideal=pressure*float(x@gas.molecular_weights)/(R*temperature)
        output.append([float(row['Z']),temperature,pr,vta,kay,ideal,error])
    data=np.asarray(output)
    assert np.isfinite(data).all() and data[:,2:6].min()>0 and data[:,-1].max()<1e-8
    args.out.mkdir(parents=True)
    np.savetxt(args.out/'density.csv',data,delimiter=',',header='Z,T,rho_PR,rho_PRVTA,rho_PRVTA_Kay,rho_ideal,PR_relative_residual',comments='')
    report={'model':'PR + Muller/Abudour volume translation; engineering mixture closure',
            'mixture_critical_primary':'EOS-equivalent a0/b; not verified as author input',
            'sensitivity':'Kay linear Tc/Pc; no parameter fitting','binary_interactions':0,
            'critical_database_sha256':digest,'profile_sha256':hashlib.sha256(args.profile.read_bytes()).hexdigest(),
            'parameters':param,'rows':len(raw),'max_PR_relative_residual':float(data[:,-1].max()),
            'raw_input_minimum_Y':minimum_y,'negative_trace_entries_preserved':negative_entries,
            'composition_qualification':'Signed trace negatives retained algebraically, not clipped or accepted as physical.',
            'oxygen_inlet':dict(zip(['PR','PRVTA','PRVTA_Kay','ideal'],data[0,2:6])),
            'methane_inlet':dict(zip(['PR','PRVTA','PRVTA_Kay','ideal'],data[-1,2:6])),
            'max_mixture_rule_density_difference':float(abs(data[:,3]-data[:,4]).max()),
            'scientific_acceptance':False}
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='parameters'},indent=2))


if __name__=='__main__':main()
