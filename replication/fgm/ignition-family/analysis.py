"""Describe actual ignition histories and progress-source/diffusion decomposition."""
from statistics import NormalDist
import numpy as np


def diagnostic(gas,grid,times,temperature,fractions,pressure,chi_st,zst,selected):
    indices=[gas.species_index(n) for n in ('CO2','CO','H2O')]
    c=fractions[:,:,indices[:2]].sum(axis=2)
    cw=c+fractions[:,:,indices[2]]
    histories=[]
    for k,t in enumerate(times):
        histories.append({'time_s':float(t),'Tmax_K':float(temperature[k].max()),
            'C_st':float(np.interp(zst,grid,c[k])), 'Cwater_st':float(np.interp(zst,grid,cw[k]))})
    chi_max=chi_st/np.exp(-NormalDist().inv_cdf(zst)**2)
    rows=[]
    for point in (.1,zst,.4,.6):
        j=int(np.argmin(abs(grid-point)))
        left,right=grid[j]-grid[j-1],grid[j+1]-grid[j]
        chi=chi_max*np.exp(-NormalDist().inv_cdf(float(grid[j]))**2)
        for n in selected:
            gas.TPY=temperature[n,j],pressure,fractions[n,j]
            omega=gas.net_production_rates*gas.molecular_weights
            second=2*(fractions[n,j-1]/(left*(left+right))-fractions[n,j]/(left*right)+fractions[n,j+1]/(right*(left+right)))
            diffusion=.5*chi*second
            row={'Z':float(grid[j]),'time_s':float(times[n]),'T_K':float(temperature[n,j]),
                'rho_kg_m3':float(gas.density),'C':float(c[n,j]),'Cwater':float(cw[n,j]),'chi_s_inverse':float(chi)}
            for label,ii in [('C',indices[:2]),('Cwater',indices)]:
                row[label+'_chemical_per_s']=float(omega[ii].sum()/gas.density)
                row[label+'_diffusion_per_s']=float(diffusion[ii].sum())
            rows.append(row)
    def reversals(values):
        result=[]
        for j,z in enumerate(grid):
            delta=np.diff(values[:,j]);sign=np.sign(delta[abs(delta)>1e-10])
            if len(sign)>1 and np.any(sign[1:]!=sign[:-1]):result.append(float(z))
        return result
    return {'schema':'seeded-flamelet-history/v1','history':histories,'progress_balance':rows,
        'old_progress_reversal_Z':reversals(c),'water_progress_reversal_Z':reversals(cw),
        'water_coordinate':'analysis candidate CO2+CO+H2O; not adopted in CFD or claimed as Sharma definition',
        'source_diffusion_note':'Native three-point nonuniform spatial stencil; physical trajectory, not homogeneous chemistry',
        'initial_peak_K':float(temperature[0].max()),'final_peak_K':float(temperature[-1].max()),
        'maximum_peak_K':float(temperature.max()),'steady_convergence_claimed':False,'scientific_acceptance':False}
