"""Fresh full-species HP reactor tails and declared ascending branch selection."""
import time
import numpy as np
from states import C,T,H,RHO,SC,Q,Y0,write_json


def integrate(ct, model, seed, settings, output):
    gas = model.gas
    gas.TPY = seed[T],settings['pressure_pa'],seed[model.ys]
    reactor = ct.IdealGasConstPressureReactor(gas,clone=True,energy='on',volume=1)
    network = ct.ReactorNet([reactor])
    network.rtol,network.atol = settings['rtol'],settings['atol']
    network.max_time_step,network.max_steps = settings['max_time_step_s'],settings['max_steps']
    times,rows = [0.0],[seed.copy()]
    mass0 = reactor.mass
    initial_elements = seed[model.ys]@model.elements
    start = time.monotonic()
    error = None
    try:
        while network.time < settings['end_time_s']:
            if len(rows) >= settings['max_steps'] or time.monotonic()-start > settings['per_tail_wall_s']:
                raise TimeoutError('Bounded chemical tail exceeded step/wall ceiling')
            actual = network.step()
            row = model.current(reactor.phase)
            if actual <= times[-1]:
                raise RuntimeError('CVODE time did not advance')
            times.append(actual);rows.append(row)
        status = 'completed'
    except Exception as exception:
        status,error = 'failed',repr(exception)
    rows,times = np.asarray(rows),np.asarray(times)
    np.savez_compressed(output/'chemical-tail.npz',time_s=times,states=rows)
    scale = max(abs(seed[H]),abs(model.gas.cp_mass*seed[T]),1)
    metrics = {'status':status,'error':error,'actual_final_time_s':float(times[-1]),
        'elapsed_s':time.monotonic()-start,'accepted_steps':len(times)-1,
        'enthalpy_relative':float(np.max(np.abs(rows[:,H]-seed[H]))/scale),
        'element_absolute':float(np.max(np.abs(rows[:,model.ys]@model.elements-initial_elements))),
        'mass_relative_final':abs(reactor.mass/mass0-1),
        'minimum_Y':float(rows[:,model.ys].min()),'initial_join_max_delta':float(np.max(np.abs(rows[0]-seed))),
        'solver_stats':network.solver_stats,'scientific_acceptance':False}
    metrics['numerically_complete'] = bool(status=='completed'
        and metrics['enthalpy_relative'] <= settings['enthalpy_relative_limit']
        and metrics['element_absolute'] <= settings['element_absolute_limit'])
    # This optional comparison cannot suppress the retained physical trace.
    try:
        gas.TPY = seed[T],settings['pressure_pa'],seed[model.ys]
        gas.equilibrate('HP',rtol=1e-10,max_steps=5000)
        equilibrium = model.current()
        metrics['HP_endpoint'] = {'T_K':float(equilibrium[T]),'Cwater':float(equilibrium[C]),
            'final_temperature_difference_K':float(rows[-1,T]-equilibrium[T]),
            'final_species_max_difference':float(np.max(np.abs(rows[-1,model.ys]-equilibrium[model.ys])))}
    except Exception as exception:
        metrics['HP_endpoint_error'] = repr(exception)
    return times,rows,metrics


def build_branch(model, raw, j, settings, output, ct):
    y,t,z = raw['Y'],raw['T_K'],raw['Z']
    water = y[:,j,model.progress].sum(axis=1)
    peak = int(water.argmax())
    available = [n for n in range(peak,len(water)) if y[n,j].min() >= 0]
    if not available:
        raise ValueError('No nonnegative actual seed is available')
    seed_index = min(available,key=lambda n:abs(t[n,j]-settings['seed_target_temperature_k']))
    seed,seed_audit = model.at_ty(t[seed_index,j],y[seed_index,j])
    write_json(output/'seed.json',{'raw_frame':seed_index,'raw_time_s':float(raw['time_s'][seed_index]),
        'Z':float(z[j]),'T_K':float(seed[T]),'Cwater':float(seed[C]),'h_J_kg':float(seed[H]),
        'representation':seed_audit,'selection':'Nearest actual postpeak nonnegative state to1500K; no temperature reset'})
    lower,lower_indices,omitted,omitted_rows,corrections = [],[],[],[],[]
    for n in range(len(water)-1,seed_index-1,-1):
        row,audit = model.at_ty(t[n,j],y[n,j],close_zero=True)
        if row[C] > seed[C] or (lower and row[C] <= lower[-1][C]+settings['progress_step_absolute']):
            omitted.append({'source':'quench','index':n,'Cwater':float(row[C]),'T_K':float(row[T]),
                            'reason':'Outside declared ascending cold-to-seed branch or numerically redundant'})
            omitted_rows.append(row)
            continue
        lower.append(row);lower_indices.append(n)
        if audit['maximum_delta_Y'] or audit['zero_tail_applied']:
            corrections.append({'raw_frame':n,**audit})
    if not lower or lower[0][C] != 0:
        raise ValueError('Actual cold branch does not reach declared numerical Cwater=0')
    if lower[-1][C] < seed[C]:
        lower.append(seed);lower_indices.append(seed_index)
    else:
        lower[-1] = seed
    times,tail,metrics = integrate(ct,model,seed,settings,output)
    if not metrics['numerically_complete']:
        write_json(output/'tail-receipt.json',metrics)
        raise ValueError('Chemical tail failed numerical completion; partial trace preserved')
    # A cap is an actual observed state, never an invented zero-source endpoint.
    inward = np.flatnonzero((tail[:,SC] <= 0) & (tail[:,C] >= seed[C]))
    cap_index = int(inward[np.argmax(tail[inward,C])]) if len(inward) else int(tail[:,C].argmax())
    cap = tail[cap_index]
    selected = list(lower)
    selected_tail = [0]
    for n in range(1,cap_index+1):
        row = tail[n]
        if row[C] > cap[C] or row[C] <= selected[-1][C]+settings['progress_step_absolute']:
            omitted.append({'source':'chemical','index':n,'Cwater':float(row[C]),'T_K':float(row[T]),
                            'reason':'Reversing/redundant state outside declared ascending chemical branch'})
            omitted_rows.append(row)
            continue
        selected.append(row);selected_tail.append(n)
    for n in range(cap_index+1,len(tail)):
        omitted.append({'source':'chemical','index':n,'Cwater':float(tail[n,C]),'T_K':float(tail[n,T]),
                        'reason':'After selected observed upper cap'})
        omitted_rows.append(tail[n])
    if cap[C] > selected[-1][C]:
        selected.append(cap);selected_tail.append(cap_index)
    elif cap[C] == selected[-1][C]:
        selected[-1] = cap
    branch = np.asarray(selected)
    if not np.all(np.diff(branch[:,C]) > 0):
        raise ValueError('Selected branch is not strictly ascending')
    differences = []
    for item,row in zip(omitted,omitted_rows):
        if branch[0,C] <= row[C] <= branch[-1,C]:
            prediction = np.asarray([np.interp(row[C],branch[:,C],branch[:,column]) for column in range(branch.shape[1])])
            item['same_C_linear_branch_temperature_difference_K'] = float(prediction[T]-row[T])
            item['same_C_linear_branch_max_Y_difference'] = float(np.max(np.abs(prediction[model.ys]-row[model.ys])))
            item['same_C_linear_branch_source_difference_kg_m3_s'] = float(prediction[SC]-row[SC])
            differences.append(abs(prediction[T]-row[T]))
        else:
            item['outside_selected_C_range'] = True
    metrics.update(Z=float(z[j]),seed_index=seed_index,seed_Cwater=float(seed[C]),
        cap_chemical_index=cap_index,cap_source_kg_m3_s=float(branch[-1,SC]),
        cap_is_inward=bool(branch[-1,SC] <= 0),raw_quench_indices=lower_indices,
        chemical_indices=selected_tail,omitted_states=omitted,representation_corrections=corrections,
        omitted_max_same_C_temperature_difference_K=float(max(differences,default=0)),
        full_chemical_max_Cwater=float(tail[:,C].max()),selected_max_Cwater=float(branch[-1,C]))
    np.savez_compressed(output/'branch.npz',states=branch)
    write_json(output/'tail-receipt.json',metrics)
    return branch,metrics
