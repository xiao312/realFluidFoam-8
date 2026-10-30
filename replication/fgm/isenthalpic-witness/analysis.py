"""Numerical same-coordinate checks and accepted-trajectory observables."""
import numpy as np
from states import C,T,H,RHO,SC,Q


def initialize(model,original,target_h):
    old=np.asarray(original['state']);y=old[model.ys]
    if y.shape!=(model.ns,) or y.min()<0 or abs(y.sum()-1)>1e-12:
        raise ValueError('Original seed composition is not a valid retained mass vector')
    row,audit=model.at_hy(target_h,y)
    corrections=[]
    for _ in range(6):
        error=float(row[H]-target_h)
        if abs(error)<=1e-6:break
        delta=error/model.gas.cp_mass
        corrections.append({'h_residual_J_kg':error,'temperature_correction_K':-delta})
        model.gas.TP=model.gas.T-delta,model.settings['pressure_pa']
        row=model.current()
    dy=float(np.max(abs(row[model.ys]-y)))
    de=float(np.max(abs((row[model.ys]-y)@model.elements)))
    dc=float(row[C]-old[C])
    report={'requested_h_J_kg':target_h,'achieved_h_J_kg':float(row[H]),
        'h_residual_J_kg':float(row[H]-target_h),'original_h_J_kg':float(old[H]),
        'enthalpy_adjustment_J_kg':float(row[H]-old[H]),'original_T_K':float(old[T]),
        'new_T_K':float(row[T]),'temperature_adjustment_K':float(row[T]-old[T]),
        'maximum_delta_Y':dy,'element_change_absolute':de,'progress_change_absolute':dc,
        'pressure_Pa':float(model.gas.P),'computed_Bilger_Z':float(model.gas.mixture_fraction('CH4:1','O2:1')),
        'HP_inversion_refinements':corrections,'representation':audit,
        'original_state':old.tolist(),'state':row.tolist(),'species_names':model.gas.species_names}
    report['qualified_initialization']=bool(abs(report['h_residual_J_kg'])<=1e-6 and dy<=1e-14 and de<=1e-12 and abs(dc)<=1e-12)
    return row,report


def pair_report(model,seeds,reports,nominal_z):
    a,b=seeds
    difference={'nominal_Z':nominal_z,'delta_Cwater':float(a[C]-b[C]),'delta_h_J_kg':float(a[H]-b[H]),
        'delta_computed_Bilger_Z':reports[0]['computed_Bilger_Z']-reports[1]['computed_Bilger_Z'],
        'delta_pressure_Pa':reports[0]['pressure_Pa']-reports[1]['pressure_Pa'],
        'maximum_element_difference':float(np.max(abs((a[model.ys]-b[model.ys])@model.elements))),
        'delta_T_K':float(a[T]-b[T]),'maximum_species_difference':float(np.max(abs(a[model.ys]-b[model.ys]))),
        'delta_Scwater_kg_m3_s':float(a[SC]-b[SC]),'delta_dC_dt_s_1':float(a[SC]/a[RHO]-b[SC]/b[RHO]),
        'delta_Qformation_W_m3':float(a[Q]-b[Q]),'scientific_acceptance':False}
    difference['qualified_equal_coordinates']=bool(all(r['qualified_initialization'] for r in reports)
        and abs(difference['delta_Cwater'])<=1e-12 and abs(difference['delta_h_J_kg'])<=2e-6
        and abs(difference['delta_computed_Bilger_Z'])<=1e-10
        and difference['maximum_element_difference']<=1e-10
        and abs(difference['delta_pressure_Pa'])<=model.settings['pressure_pa']*1e-12)
    return difference


def observables(times,rows):
    crossings={}
    for delta in [.01,.1,.2]:
        reached=np.flatnonzero(rows[:,C]>=rows[0,C]+delta)
        index=int(reached[0]) if len(reached) else None
        crossings[str(delta)]={'first_accepted_time_s':float(times[index]) if index is not None else None,
            'bracket_s':[float(times[max(0,index-1)]),float(times[index])] if index is not None else None}
    return {'progress_increment_crossings':crossings,'minimum_Cwater':float(rows[:,C].min()),
        'maximum_Cwater':float(rows[:,C].max()),'upward_steps_over_1e_9':int(np.count_nonzero(np.diff(rows[:,C])>1e-9)),
        'downward_steps_over_1e_9':int(np.count_nonzero(np.diff(rows[:,C])<-1e-9)),
        'final_Cwater':float(rows[-1,C]),'final_T_K':float(rows[-1,T])}
