"""Tabulate measured branches; report independent-Z errors without acceptance."""
import numpy as np
from states import C,T,H,RHO,SC,Q,write_json


def evaluate_branch(model, branch, progress):
    if progress == branch[0,C] or progress == branch[-1,C]:
        row = branch[0] if progress == branch[0,C] else branch[-1]
        if row[model.ys].min() < 0:
            raise ValueError('Observed endpoint has a negative species; no implicit endpoint repair')
        # Preserve the measured endpoint/source exactly rather than perturbing an
        # equilibrium-scale source sign with an unnecessary HP round-trip.
        return row.copy()
    if len(branch) == 1:
        if progress != branch[0,C]:
            raise ValueError('Pure stream has no progress span')
        return branch[0].copy()
    if not branch[0,C] <= progress <= branch[-1,C]:
        raise ValueError('Query outside physical branch')
    y = np.array([np.interp(progress,branch[:,C],branch[:,k]) for k in range(model.ys.start,model.ys.stop)])
    h = float(np.interp(progress,branch[:,C],branch[:,H]))
    row,_ = model.at_hy(h,y)
    if abs(row[C]-progress) > 1e-12:
        raise ValueError('Progress/composition interpolation mismatch')
    return row


def summarize_errors(differences, truth, names):
    if not len(differences):
        return {'count':0}
    delta,expected = np.asarray(differences),np.asarray(truth)
    result = {'count':len(delta),'fields':{}}
    for k,name in enumerate(names):
        peak = float(np.max(np.abs(expected[:,k])))
        result['fields'][name] = {'rms':float(np.sqrt(np.mean(delta[:,k]**2))),
            'max_absolute':float(np.max(np.abs(delta[:,k]))),'true_global_peak':peak,
            'rms_over_true_global_peak':float(np.sqrt(np.mean(delta[:,k]**2))/peak) if peak else None}
    return result


def build(model, branches, reports, z, settings, out):
    train = np.arange(0,len(z),2)
    intended_heldout = list(range(1,len(z),2))
    heldout = [j for j in intended_heldout if j in branches]
    eta = np.linspace(0,1,settings['eta_points'])
    axis = z[train]
    limits = np.asarray([[branches[j][0,C],branches[j][-1,C]] for j in train])
    values = np.stack([np.stack([evaluate_branch(model,branches[j],low+v*(high-low)) for v in eta])
                       for j,(low,high) in zip(train,limits)])
    np.savez_compressed(out/'table.npz',Z=axis,eta=eta,Cmin=limits[:,0],Cmax=limits[:,1],states=values)
    fields = ['T_K','rho_kg_m3','h_J_kg','Scwater_kg_m3_s','Qformation_W_m3']+['Y_'+n for n in model.gas.species_names]
    positions = [T,RHO,H,SC,Q]+list(range(model.ys.start,model.ys.stop))
    errors,truth,coverage_failures,witnesses = [],[],[],[]
    for j in heldout:
        own = branches[j]
        low,high = float(np.interp(z[j],axis,limits[:,0])),float(np.interp(z[j],axis,limits[:,1]))
        left = int(np.searchsorted(axis,z[j])-1)
        fraction_z = float((z[j]-axis[left])/(axis[left+1]-axis[left]))
        at_z = (1-fraction_z)*values[left]+fraction_z*values[left+1]
        for fraction in np.linspace(0,1,settings['heldout_eta_points']):
            c = own[0,C]+fraction*(own[-1,C]-own[0,C])
            actual = evaluate_branch(model,own,c)
            if not low <= c <= high or high == low:
                coverage_failures.append({'Z':float(z[j]),'Cwater':float(c),'training_Cmin':low,'training_Cmax':high})
                continue
            coordinate = (c-low)/(high-low)
            prediction = np.asarray([np.interp(coordinate,eta,at_z[:,column]) for column in range(values.shape[2])])
            differences = prediction[positions]-actual[positions]
            errors.append(differences);truth.append(actual[positions])
            if len(witnesses)<12 and abs(differences[3]) > max(abs(actual[SC]),1):
                witnesses.append({'Z':float(z[j]),'Cwater':float(c),'actual_Scwater':float(actual[SC]),
                                  'predicted_Scwater':float(prediction[SC]),'actual_T_K':float(actual[T]),
                                  'predicted_T_K':float(prediction[T])})
    held = summarize_errors(errors,truth,fields)
    held.update(independent_Z_indices=heldout,intended_heldout_Z_indices=intended_heldout,
        missing_heldout_Z_indices=[j for j in intended_heldout if j not in branches],training_Z_indices=train.tolist(),
        coverage_failures=coverage_failures,source_error_witnesses=witnesses,
        source_note='RMS/global peak is separate from near-zero relative errors; no pass criterion is invented',
        scientific_acceptance=False)
    write_json(out/'heldout.json',held)
    projection = []
    for i,j in enumerate(train):
        span = limits[i,1]-limits[i,0]
        if span == 0:
            continue
        caxis = limits[i,0]+eta*span
        tangent = np.gradient(values[i,:,model.ys],caxis,axis=0,edge_order=2)
        projected_q = -(tangent@model.hf)*values[i,:,SC]
        delta = projected_q-values[i,:,Q]
        for region,mask in [('cold',(caxis < reports[j]['seed_Cwater'])),('chemical',(caxis >= reports[j]['seed_Cwater']))]:
            if not np.any(mask):
                continue
            q = values[i,mask,Q]
            peak = max(float(np.max(np.abs(q))),1)
            projection.append({'Z':float(z[j]),'region':region,'nodes':int(mask.sum()),
                'Q_error_rms_W_m3':float(np.sqrt(np.mean(delta[mask]**2))),
                'Q_error_rms_over_region_peak':float(np.sqrt(np.mean(delta[mask]**2))/peak),
                'true_region_Q_peak_W_m3':float(np.max(np.abs(q)))})
    upper = [{'Z':float(z[j]),'Cmax':float(limits[i,1]),'Scwater':float(values[i,-1,SC])} for i,j in enumerate(train)]
    lower = [{'Z':float(z[j]),'Cmin':float(limits[i,0]),'Scwater':float(values[i,0,SC])} for i,j in enumerate(train)]
    element = values[:,:,model.ys]@model.elements
    expected = (1-axis[:,None])*element[0,0][None,:]+axis[:,None]*element[-1,0][None,:]
    diagnostics = {'upper_source_bounds':upper,'lower_source_bounds':lower,
        'outward_upper_nodes':[row for row in upper if row['Scwater'] > 0],
        'outward_lower_nodes':[row for row in lower if row['Scwater'] < 0],
        'maximum_element_error':float(np.max(np.abs(element-expected[:,None,:]))),
        'maximum_species_sum_error':float(np.max(np.abs(values[:,:,model.ys].sum(axis=2)-1))),
        'minimum_Y':float(values[:,:,model.ys].min()),'maximum_T_K':float(values[:,:,T].max()),
        'interpolation_representation':model.interpolation_representation,
        'source_projection':projection,'scientific_acceptance':False}
    write_json(out/'diagnostics.json',diagnostics)
    return axis,eta,limits,values,diagnostics


def write_table(path, model, axis, eta, limits, values, source, profile_hash):
    fmt = lambda numbers: ' '.join(format(float(v),'.17g') for v in numbers)
    lines = ['schema forge-fgm-table-v2','source hybrid-water-'+source,'profile-sha256 '+profile_hash,
        'units-progress-source kg/m3/s','units-heat-release W/m3',
        'density-owner thermophysicalModel','temperature-owner thermophysicalModel','enthalpy-owner thermophysicalModel',
        'progress-coordinate mass-fraction-mapped','progress-species '+' '.join(model.settings['progress_species']),
        'species '+' '.join(model.gas.species_names),'nZ '+str(len(axis)),'nC '+str(len(eta)),
        'z '+fmt(axis),'c '+fmt(eta),'c-min '+fmt(limits[:,0]),'c-max '+fmt(limits[:,1])]
    blocks = [('Y '+name,model.ys.start+k) for k,name in enumerate(model.gas.species_names)]
    blocks += [('Sc',SC),('Q',Q),('Tdiag',T)]
    for name,column in blocks:
        lines += ['block '+name]+[fmt(row) for row in values[:,:,column]]+['end']
    path.write_text('\n'.join(lines)+'\n',encoding='ascii')
