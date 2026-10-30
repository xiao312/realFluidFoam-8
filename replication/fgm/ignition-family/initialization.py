"""Fresh compact product seed at the original inlet-mixed total enthalpy."""
import numpy as np


def prepare(gas, mechanism, streams, config, settings, grid):
    zst=1/(1+gas.stoich_air_fuel_ratio(config['fuel']['mole_fractions'],config['oxidizer']['mole_fractions'],basis='mole'))
    seed=settings['seed']; width=seed['mixture_fraction_half_width']
    alpha=np.where(abs(grid-zst)<width,seed['peak_product_fraction']*.5*(1+np.cos(np.pi*(grid-zst)/width)),0)
    alpha[[0,-1]]=0
    weights=np.array([[gas.n_atoms(k,e)*gas.atomic_weight(e)/gas.molecular_weights[k]
                      for e in gas.element_names] for k in range(gas.n_species)])
    temperatures=[];fractions=[];enthalpy_errors=[];element_errors=[];source_rows=[]
    for i,z in enumerate(grid):
        mixed=z*streams['fuel']['Y']+(1-z)*streams['oxidizer']['Y']
        h=z*streams['fuel']['h']+(1-z)*streams['oxidizer']['h']
        gas.HPY=h,config['pressure_pa'],mixed
        if alpha[i]>0:
            gas.equilibrate('HP')
            initial_y=(1-alpha[i])*mixed+alpha[i]*gas.Y
            gas.HPY=h,config['pressure_pa'],initial_y
        if i==0 or i==len(grid)-1:
            stream=streams['oxidizer' if i==0 else 'fuel']
            gas.TPY=stream['temperature'],config['pressure_pa'],stream['Y']
        y=gas.Y.copy();t=gas.T
        temperatures.append(t);fractions.append(y)
        enthalpy_errors.append(float(gas.enthalpy_mass-h))
        element_errors.append(float(np.max(abs((y-mixed)@weights))))
        ct_rate=gas.net_production_rates*gas.molecular_weights
        griffon_rate=np.zeros(gas.n_species)
        mechanism.griffon.production_rates(t,gas.density,y,griffon_rate)
        source_rows.append({'Z':float(z),'T_K':float(t),
            'cantera_finite':bool(np.isfinite(ct_rate).all()),'griffon_finite':bool(np.isfinite(griffon_rate).all()),
            'peak_mass_source_kg_m3_s':float(np.max(abs(griffon_rate))) if np.isfinite(griffon_rate).all() else None,
            'peak_scaled_rate_error':float(np.max(abs(griffon_rate-ct_rate))/max(np.max(abs(ct_rate)),1))
                if np.isfinite(ct_rate).all() and np.isfinite(griffon_rate).all() else None})
    t=np.array(temperatures);y=np.array(fractions)
    limits=settings['initialization_limits']
    metrics={'kind':'fresh compact equilibrium-product seed at conserved inlet-mixed enthalpy',
        'stoichiometric_Z':zst,'seed':seed,'enthalpy_error_max_J_kg':float(np.max(np.abs(enthalpy_errors))),
        'element_error_max':max(element_errors),'species_sum_error_max':float(np.max(abs(y.sum(axis=1)-1))),
        'species_min':float(y.min()),'temperature_min_K':float(t.min()),'temperature_max_K':float(t.max()),
        'pure_endpoints_exact':bool(np.array_equal(y[0],streams['oxidizer']['Y']) and np.array_equal(y[-1],streams['fuel']['Y'])
            and t[0]==streams['oxidizer']['temperature'] and t[-1]==streams['fuel']['temperature']),
        'finite_sources':all(r['cantera_finite'] and r['griffon_finite'] for r in source_rows),
        'source_nodes':source_rows,'limits':limits,'scientific_acceptance':False}
    metrics['initialization_checks_passed']=bool(metrics['enthalpy_error_max_J_kg']<=limits['enthalpy_absolute_J_kg']
        and metrics['element_error_max']<=limits['element_absolute'] and metrics['species_sum_error_max']<=limits['mass_sum_absolute']
        and metrics['species_min']>=0 and np.isfinite(t).all() and np.all(t>0)
        and metrics['pure_endpoints_exact'] and metrics['finite_sources'])
    return t,y,alpha,metrics
