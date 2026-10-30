"""Exact-state mixture construction and bounded table lookup; no source alteration."""
import numpy as np


def seeds(data):
    z,v=data['Z'],data['states']
    lean=int(np.argmin(abs(z-.1972101463962859)))
    rich=int(np.argmin(abs(z-.4325725801849406)))
    assert abs(z[lean]-.1972101463962859)<1e-14
    assert abs(z[rich]-.4325725801849406)<1e-14
    points={'lean_cap':(float(z[lean]),v[lean,-1]),'rich_cap':(float(z[rich]),v[rich,-1]),
            'CH4':(1.0,v[-1,0]),'O2':(0.0,v[0,0])}
    recipes=[]
    for target,name in [(.48531925567740947,'missing-Z0485'),(.5050322757881766,'missing-Z0505')]:
        fuel=(target-z[rich])/(1-z[rich])
        recipes.append({'name':name,'Z':target,'weights':{'rich_cap':float(1-fuel),'CH4':float(fuel)}})
    target=.286519345725
    rich_weight=target/z[rich]
    c=rich_weight*v[rich,-1,0]
    lean_weight=c/v[lean,-1,0]
    fuel_weight=target-lean_weight*z[lean]
    recipes.extend([
        {'name':'same-ZC-rich-path','Z':target,'weights':{'rich_cap':float(rich_weight),'O2':float(1-rich_weight)}},
        {'name':'same-ZC-lean-path','Z':target,'weights':{'lean_cap':float(lean_weight),'CH4':float(fuel_weight),'O2':float(1-lean_weight-fuel_weight)}}])
    for recipe in recipes:
        assert min(recipe['weights'].values())>=0 and abs(sum(recipe['weights'].values())-1)<1e-14
        assert abs(sum(points[key][0]*weight for key,weight in recipe['weights'].items())-recipe['Z'])<1e-14
    return points,recipes


def lookup(data,z,c):
    axis,eta,v=data['Z'],data['eta'],data['states']
    if not axis[0]<=z<=axis[-1]:return None
    i=min(max(int(np.searchsorted(axis,z))-1,0),len(axis)-2)
    a=(z-axis[i])/(axis[i+1]-axis[i])
    low=float(np.interp(z,axis,data['Cmin']));high=float(np.interp(z,axis,data['Cmax']))
    if c<low or c>high or high==low:return None
    at_z=(1-a)*v[i]+a*v[i+1]
    coordinate=(c-low)/(high-low)
    return np.asarray([np.interp(coordinate,eta,at_z[:,k]) for k in range(v.shape[2])])


def compare(data,z,states,ys):
    errors=[];truth=[];outside=0
    for row in states:
        prediction=lookup(data,z,float(row[0]))
        if prediction is None:
            outside+=1;continue
        columns=[1,2,4,5]
        errors.append([*(prediction[columns]-row[columns]),float(np.max(np.abs(prediction[ys]-row[ys])))])
        truth.append(row[columns])
    report={'covered_states':len(errors),'outside_states':outside,'no_clamping':True,'scientific_acceptance':False}
    if errors:
        errors=np.asarray(errors);truth=np.asarray(truth)
        report['fields']={}
        for k,name in enumerate(['T_K','h_J_kg','Scwater_kg_m3_s','Qformation_W_m3']):
            peak=float(np.max(np.abs(truth[:,k])))
            report['fields'][name]={'rms':float(np.sqrt(np.mean(errors[:,k]**2))),
                'max_absolute':float(np.max(np.abs(errors[:,k]))),'actual_peak':peak,
                'rms_over_actual_peak':float(np.sqrt(np.mean(errors[:,k]**2))/peak) if peak else None}
        report['maximum_same_coordinate_species_difference']=float(errors[:,-1].max())
    return report
