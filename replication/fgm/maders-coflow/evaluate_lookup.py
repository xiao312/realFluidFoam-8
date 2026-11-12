"""Independent fixed held-out metrics; does not change candidate or reference data."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    ref=np.load(a.reference);pred=np.load(a.predictions)
    mask=pred['covered'].astype(bool)
    n=len(ref['T'])
    if mask.shape!=(n,) or pred['T'].shape!=(n,) or pred['Y'].shape!=ref['Y'].shape or pred['Sc_kg_m3_s'].shape!=(n,):
        raise ValueError('Prediction dimensions differ from fixed query set')
    if not mask.any():raise ValueError('No covered states; physical metrics undefined')
    if any(not np.isfinite(pred[k][mask]).all() for k in ['T','Y','Sc_kg_m3_s']):
        raise ValueError('Covered predictions contain nonfinite values')
    errors={}
    for key in ['T','Sc_kg_m3_s']:
        delta=pred[key][mask]-ref[key][mask]
        errors[key]={'RMSE':float(np.sqrt(np.mean(delta**2))),'max_abs':float(abs(delta).max())}
    delta=pred['Y'][mask]-ref['Y'][mask]
    source_scale=max(float(abs(ref['Sc_kg_m3_s']).max()),1e-12)
    relevant=mask & (abs(ref['Sc_kg_m3_s'])>1e-4*source_scale)
    report={'schema':'maders-fixed-heldout-lookup/v1','queries':n,'covered':int(mask.sum()),
        'coverage':float(mask.mean()),'errors':errors,
        'species_RMSE':dict(zip(ref['species'].tolist(),np.sqrt(np.mean(delta**2,axis=0)).tolist())),
        'max_abs_species_error':float(abs(delta).max()),
        'minimum_predicted_Y':float(pred['Y'][mask].min()),
        'max_mass_sum_error':float(abs(pred['Y'][mask].sum(axis=1)-1).max()),
        'max_weighted_C_error':float(abs(pred['Y'][mask]@ref['progress_weights']-ref['C'][mask]).max()),
        'nontrivial_source_sign_errors':int(((pred['Sc_kg_m3_s'][relevant]*ref['Sc_kg_m3_s'][relevant])<0).sum()),
        'source_global_peak_kg_m3_s':source_scale,
        'reference_sha256':hashlib.sha256(a.reference.read_bytes()).hexdigest(),
        'predictions_sha256':hashlib.sha256(a.predictions.read_bytes()).hexdigest(),
        'scientific_acceptance':False,
        'limits':'Interpolation metrics on two held-out physical flamelets; not coflow CFD or paper acceptance. Uncovered states remain failures of coverage.'}
    if a.out.exists():raise ValueError('Refusing existing metric receipt')
    a.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
