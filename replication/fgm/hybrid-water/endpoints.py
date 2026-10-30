"""Apply the existing explicit numerical endpoint policy with before/after evidence."""
from states import C,T


def represent(model,branches,z):
    corrections=[]
    for j,branch in branches.items():
        for side,index in [('lower',0),('upper',-1)]:
            before=branch[index].copy()
            if before[model.ys].min()>=0:
                continue
            after,audit=model.at_ty(before[T],before[model.ys])
            assert abs(after[C]-before[C])<=1e-12, 'Representation changed the progress coordinate'
            corrections.append({'Z_index':j,'Z':float(z[j]),'endpoint':side,**audit,
                'species_names':model.gas.species_names,
                'Y_before':before[model.ys].tolist(),'Y_after':after[model.ys].tolist(),
                'element_names':model.gas.element_names,
                'elements_before':(before[model.ys]@model.elements).tolist(),
                'elements_after':(after[model.ys]@model.elements).tolist(),
                'before':dict(zip(['Cwater','T_K','h_J_kg','rho_kg_m3','Scwater_kg_m3_s','Qformation_W_m3'],before[:6].tolist())),
                'after':dict(zip(['Cwater','T_K','h_J_kg','rho_kg_m3','Scwater_kg_m3_s','Qformation_W_m3'],after[:6].tolist()))})
            branch[index]=after
    return {'policy':'existing-bounded-roundoff-v1',
        'unchanged_negative_limit':model.settings['roundoff_negative_limit'],
        'unchanged_change_limit':model.settings['roundoff_change_limit'],'states':corrections}
