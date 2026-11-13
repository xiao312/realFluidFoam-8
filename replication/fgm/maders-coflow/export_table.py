"""Export a weighted physical FGM candidate, with explicit cold/equilibrium limits."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import platform
import numpy as np
import cantera as ct
from lookup_baseline import query


def digest(file):return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profiles',type=Path,required=True)
    p.add_argument('--mechanism',type=Path,required=True)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--profile-origin',type=Path)
    p.add_argument('--family-manifest',type=Path)
    p.add_argument('--environment-sha256',required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--plan',action='store_true')
    a=p.parse_args()
    selected=[0,1,4,5,6]  # chi5/10 remain independent held-out profiles.
    files=[a.profiles/f'chi-{i:02d}/profile.npz' for i in selected]
    if a.family_manifest:
        family=json.loads(a.family_manifest.read_text())
        if family.get('schema')!='maders-quenching-family/v1':raise ValueError('Unknown family manifest')
        if not family.get('quenching_reached_cold'):raise ValueError('Quenching path incomplete; retain evidence before export')
        rows=[r for r in family['profiles'] if r['finite'] and r.get('solver_error') is None
              and (r['kind']=='transient-quenching' or
                   (r['steady_residual_pass'] and r['chi_st_s_inverse'] not in [5.,10.]))]
        files=[a.family_manifest.parent/r['profile'] for r in rows]
        origin={'family_manifest_sha256':digest(a.family_manifest),
                'physical_family':family,'profile_hashes':{r['profile']:r['sha256'] for r in rows},
                'withheld_steady_chi':[5.,10.]}
        if not files:raise ValueError('No eligible physical training members')
    elif a.profile_origin:
        origin=json.loads(a.profile_origin.read_text())
    else:raise ValueError('Require --profile-origin or --family-manifest')
    if a.plan:
        print(json.dumps({'profiles':[str(f) for f in files], 'weighted_progress':True,
            'limits':'Explicit cold mixed reactants and HP equilibrium; no curve fitting',
            'format':'forge-fgm-table-v3','out':str(a.out)}));return
    if len(a.source_commit)!=40 or len(a.environment_sha256)!=64:
        raise ValueError('Exact source and environment identities required')
    for file in files:
        key=str(file.relative_to(a.family_manifest.parent if a.family_manifest else a.profiles)).replace('\\','/')
        if origin['profile_hashes'].get(key)!=digest(file):raise ValueError('Profile identity differs: '+key)
    a.out.mkdir(parents=True,exist_ok=False)
    gas=ct.Solution(str(a.mechanism))
    profiles=[np.load(file) for file in files]
    z=profiles[0]['Z'];weights=profiles[0]['progress_weights'];species=gas.species_names
    if any(not np.array_equal(d['Z'],z) or not np.array_equal(d['species'],species) for d in profiles):
        raise ValueError('Input grids/species differ')
    gas.TP=298.15,101325.;h0=gas.partial_molar_enthalpies/gas.molecular_weights
    gas.TPX=298.,101325.,{'CH4':.55,'N2':.45};yf=gas.Y.copy();hf=gas.enthalpy_mass
    gas.TPX=298.,101325.,{'O2':1,'N2':3.76};ya=gas.Y.copy();ha=gas.enthalpy_mass
    limits=[[],[]]
    for mixture in z:
        unburnt=mixture*yf+(1-mixture)*ya;h=mixture*hf+(1-mixture)*ha
        for k in range(2):
            gas.HPY=h,101325.,unburnt
            if k and 0<mixture<1:gas.equilibrate('HP')
            omega=gas.net_production_rates*gas.molecular_weights
            limits[k].append([float(gas.Y@weights),gas.T,float(omega@weights),float(-omega@h0),*gas.Y])
    all_profiles=[np.column_stack([d['C'],d['T'],d['Sc_kg_m3_s'], -(d['omega_kg_m3_s']@h0),d['Y']]) for d in profiles]
    all_profiles += [np.asarray(limit) for limit in limits]
    row_models=[];duplicate_spread=[]
    for j in range(len(z)):
        values=np.array([d[j] for d in all_profiles])
        values=values[np.argsort(values[:,0])]
        c,first,counts=np.unique(values[:,0],return_index=True,return_counts=True)
        for start,count in zip(first,counts):
            if count>1:
                # Pure-stream chemistry is the same state; do not merge different branches.
                spread=np.max(abs(values[start:start+count,1:]-values[start,1:]))
                duplicate_spread.append(float(spread))
                if spread>1e-6:raise ValueError(f'Ambiguous duplicate C at Z={z[j]}')
        row_models.append((c,values[first,1:]))
    model=(z,row_models);eta=np.linspace(0,1,len(z) if a.family_manifest else 129)
    lower=np.array([row[0][0] for row in row_models]);upper=np.array([row[0][-1] for row in row_models])
    values=[]
    for j,mixture in enumerate(z):
        values.append([query(model,float(mixture),float(lower[j]+e*(upper[j]-lower[j]))) for e in eta])
    values=np.asarray(values)
    y=values[:,:,3:];c=lower[:,None]+eta[None,:]*(upper-lower)[:,None]
    if not np.isfinite(values).all() or y.min() < -1e-12 or np.max(abs(y.sum(axis=2)-1))>1e-8:
        raise ValueError('Physical table fails finite/composition checks; no clipping applied')
    if np.max(abs(y@weights-c))>1e-8:raise ValueError('Weighted progress reconstruction fails')
    number=lambda arr:' '.join(format(float(v),'.17g') for v in arr)
    progress_species=['CO2','H2O','H2'];w=[weights[gas.species_index(s)] for s in progress_species]
    combined=digest(files[0])
    combined=hashlib.sha256(''.join(digest(file) for file in files).encode()).hexdigest()
    lines=['schema forge-fgm-table-v3','source '+a.source_commit,'profile-sha256 '+combined,
        'units-progress-source kg/m3/s','units-heat-release W/m3','density-owner thermophysicalModel',
        'temperature-owner thermophysicalModel','enthalpy-owner thermophysicalModel',
        'progress-coordinate weighted-mass-fraction-mapped','progress-species '+' '.join(progress_species),
        'progress-weights '+number(w),'species '+' '.join(species),'nZ '+str(len(z)),'nC '+str(len(eta)),
        'z '+number(z),'c '+number(eta),'c-min '+number(lower),'c-max '+number(upper)]
    blocks=[('Y '+name,y[:,:,i]) for i,name in enumerate(species)]
    blocks += [('Sc',values[:,:,1]),('Q',values[:,:,2]),('Tdiag',values[:,:,0])]
    for name,array in blocks:lines += ['block '+name]+[number(row) for row in array]+['end']
    (a.out/'physical.tbl').write_text('\n'.join(lines)+'\n')
    np.savez_compressed(a.out/'table.npz',Z=z,eta=eta,c_min=lower,c_max=upper,values=values,
        species=species,progress_weights=weights)
    # Exact physical table nodes for the existing independent C++ reader probe.
    node_indices=[(i,j) for i in sorted(set([0,1,len(z)//8,len(z)//2,len(z)-2,len(z)-1]))
                  for j in sorted(set([0,1,len(eta)//4,len(eta)//2,len(eta)-2,len(eta)-1]))]
    node_lines=[f'{len(species)} {len(node_indices)}']
    for i,j in node_indices:
        node_lines.append(number([z[i],c[i,j],values[i,j,1],values[i,j,2],values[i,j,0],*y[i,j]]))
    (a.out/'reader-nodes.txt').write_text('\n'.join(node_lines)+'\n')
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'direct-flamelet'))
    from metadata import phase_metadata
    metadata=phase_metadata(ct,gas,a.mechanism,digest(a.mechanism),a.source_commit,a.environment_sha256)
    (a.out/'phase-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    # A hot, near-source-peak seed at the physical stoichiometric mixture fraction.
    zst=1/(1+gas.stoich_air_fuel_ratio({'CH4':.55,'N2':.45},{'O2':1,'N2':3.76},basis='mole'))
    lo=np.interp(zst,z,lower);hi=np.interp(zst,z,upper)
    candidates=[(lo+e*(hi-lo),query(model,zst,float(lo+e*(hi-lo)))) for e in np.linspace(.05,.95,91)]
    hot_c,hot=max(candidates,key=lambda item:item[1][1])
    gas.HPY=zst*hf+(1-zst)*ha,101325.,hot[3:]
    init={'Z':zst,'C':float(hot_c),'Y':gas.Y.tolist(),'T_K':gas.T,'Ha_J_kg':gas.enthalpy_mass,
        'cold_air_Y':ya.tolist(),'cold_fuel_Y':yf.tolist(),'cold_air_Ha_J_kg':ha,'cold_fuel_Ha_J_kg':hf,
        'note':'Fresh time-zero hot ring near burner exit; no evolved cold-flow field. This differs from the paper cold-steady-first numerical sequence.'}
    (a.out/'initialization.json').write_text(json.dumps(init,indent=2)+'\n')
    receipt={'schema':'maders-weighted-physical-table/v1','source_commit':a.source_commit,
        'mechanism_sha256':digest(a.mechanism),'environment_sha256':a.environment_sha256,
        'processing_environment':{'platform':platform.platform(),'python':platform.python_version(),'cantera':ct.__version__,'numpy':np.__version__},'profile_origin':origin,'profile_hashes':{str(f):digest(f) for f in files},'table_sha256':digest(a.out/'physical.tbl'),
        'metadata_sha256':digest(a.out/'phase-metadata.json'),'nZ':len(z),'nC':len(eta),
        'minimum_Y':float(y.min()),'max_mass_sum_error':float(abs(y.sum(axis=2)-1).max()),
        'max_weighted_C_error':float(abs(y@weights-c).max()),'cold_equilibrium_limits_added':True,
        'duplicate_state_max_spread':max(duplicate_spread,default=0),
        'limits':('Denser steady/transient quenching family plus cold/HP-equilibrium limits; finite sampling still uses linear interpolation; prescribed Peters chi is not resolved strain.' if a.family_manifest else 'Reconstructed finite family plus explicit cold/HP-equilibrium limits; unsampled progress gaps are linearly interpolated, not additional solved steady flamelets.'),
        'scientific_acceptance':False}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
