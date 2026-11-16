"""Verify physical definitions for a sampling refinement, without accepting its errors."""
import argparse
import json
from pathlib import Path
import numpy as np
from qualify_export_grid import load,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--plan',action='store_true')
    a=p.parse_args()
    if a.plan:
        print(json.dumps({'baseline':str(a.baseline),'candidate':str(a.candidate),
            'unchanged':'mechanism,thermodynamic properties,streams,progress weights,Z/eta axes',
            'out':str(a.out),'physicalMetricsAccepted':False}));return
    br,bm,bi,b=load(a.baseline);cr,cm,ci,c=load(a.candidate)
    for key in ['mechanism_sha256','environment_sha256','nZ','nC']:
        if br[key]!=cr[key]:raise ValueError('Changed definition '+key)
    for key in ['schema','canteraVersion','mechanismSha256','thermoModel','phase',
                'gasConstant_J_kmol_K','speciesOrder','species','transportModelQualified']:
        if bm[key]!=cm[key]:raise ValueError('Changed thermo '+key)
    for key in ['cold_air_Y','cold_fuel_Y','cold_air_Ha_J_kg','cold_fuel_Ha_J_kg']:
        if bi[key]!=ci[key]:raise ValueError('Changed stream '+key)
    for key in ['Z','eta','species','progress_weights']:
        if not np.array_equal(b[key],c[key]):raise ValueError('Changed coordinate/progress '+key)
    family=cr['profile_origin']['physical_family']
    if not family.get('withheld_transient_times_s'):
        raise ValueError('Refinement needs explicitly withheld temporal states')
    selected=set(cr['profile_origin']['profile_hashes'])
    held={r['profile']for r in family['profiles']if r.get('held_out')}
    if not held or selected&held:raise ValueError('Temporal hold-out leaked into training')
    y=c['values'][:,:,3:]
    if not np.isfinite(c['values']).all():raise ValueError('Nonfinite candidate table')
    progress=c['c_min'][:,None]+c['eta'][None,:]*(c['c_max']-c['c_min'])[:,None]
    mass=float(np.max(abs(y.sum(axis=2)-1)))
    c_error=float(np.max(abs(y@c['progress_weights']-progress)))
    beta=np.array([(2*s['composition'].get('C',0)+.5*s['composition'].get('H',0)
                   -s['composition'].get('O',0))/s['molecularWeight_kg_kmol']for s in cm['species']])
    bf=float(np.array(ci['cold_fuel_Y'])@beta);ba=float(np.array(ci['cold_air_Y'])@beta)
    z_error=float(np.max(abs((y@beta-ba)/(bf-ba)-c['Z'][:,None])))
    if mass>1e-8 or c_error>1e-8 or z_error>1e-8 or y.min()<-1e-12:
        raise ValueError('Existing mass/progress/element/species criteria failed')
    report={'baselineTableSha256':br['table_sha256'],'candidateTableSha256':cr['table_sha256'],
      'ASCII_NPZ_identity':True,'physicalDefinitionsUnchanged':True,
      'heldOutProfiles':len(held),'trainingProfiles':len(selected),'holdOutLeakage':False,
      'maximumMassError':mass,'maximumWeightedProgressError':c_error,
      'maximumSpeciesDerivedZError':z_error,'minimumRawY':float(y.min()),
      'maximumCminChange':float(np.max(abs(c['c_min']-b['c_min']))),
      'maximumCmaxChange':float(np.max(abs(c['c_max']-b['c_max']))),
      'scriptSha256':sha(Path(__file__)),'physicalMetricsAccepted':False,
      'scientificAcceptance':False,'note':'Run unchanged steady and separate temporal held-out evaluators; structural qualification is not a good-error verdict.'}
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
