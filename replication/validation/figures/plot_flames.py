"""Plot paper-matched counterflow diagnostics from non-converged pilot fields."""
import csv
import os
import sys
from pathlib import Path
import numpy as np
from foam_fields import read_case
root = Path(sys.argv[1]).resolve(strict=True)
os.environ['MPLCONFIGDIR'] = str(root/'cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
out = root/'output/figure-comparison-20261017'
plt.rcParams.update({'font.family':'DejaVu Serif', 'font.size':10, 'axes.formatter.useoffset':False})
cases = {}
for name, job in [('oxy-1',124660430),('oxy-200',124660583),('air-100',124660669)]:
    xyz, f, time = read_case(root/f'state/flame-pilots-20261017/jobs/{job}/{name}')
    radial = np.hypot(xyz[:,0],xyz[:,1])
    indices = np.flatnonzero(np.isclose(radial,radial.min(),atol=1e-9,rtol=0))
    indices = indices[np.argsort(xyz[indices,2])]
    cases[name] = (xyz,f,time,indices,radial.min())
    with (out/f'data/{name}-nearest-axis.csv').open('w',newline='') as stream:
        writer=csv.writer(stream); names=[n for n in f if n!='U']
        writer.writerow(['z_m','r_m',*names])
        writer.writerows([[xyz[i,2],radial[i],*[f[n][i] for n in names]] for i in indices])

def finish(fig, number, foot):
    fig.suptitle(f'2022 Figure {number} - STARTUP ONLY / NOT REPLICATED',fontsize=14,y=.99,color='#9b3020')
    fig.text(.5,.02,foot,ha='center',fontsize=9)
    fig.savefig(out/f'plots/2022-fig{number:02}.png',dpi=180)
    fig.savefig(out/f'plots/2022-fig{number:02}.svg')
    plt.close(fig)

def line(ax,z,y,label,color):
    ax.plot(z,y,'o-',ms=3,lw=1,color=color,label=label)
    ax.set_xlabel('Axial distance z [m]')
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.ticklabel_format(axis='y',style='sci',scilimits=(-3,4))

for name,number,window,ohscale in [('oxy-1',9,(.003,.018),100),('oxy-200',10,(.002,.0035),500)]:
    xyz,f,t,idx,r=cases[name]; z=xyz[idx,2]
    fig,axes=plt.subplots(2,2,figsize=(11,7.4))
    fig.subplots_adjust(top=.88,bottom=.13,left=.09,right=.90,hspace=.38,wspace=.55)
    a,b,c,d=axes.flat
    line(a,z,f['T'][idx],'T','#bd2525'); a.set_ylabel('Temperature [K]'); a.set_ylim(0,3500)
    for n,color in [('CH4','#242424'),('O2','#b32424'),('CO2','#2278a5'),('H2O','#2a8033'),('OH','#8c43aa')]:
        line(b,z,f[n][idx]*(ohscale if n=='OH' else 1),f'OH x {ohscale}' if n=='OH' else n,color)
    b.set_ylabel('Mass fraction');b.set_ylim(0,1);b.legend(fontsize=8,ncol=2)
    for ax,left,right,lab1,lab2 in [(c,'rho','Cp','Density [kg/m³]','Cp [J/(kg K)]'),(d,'mu','kappa','Viscosity [Pa s]','Conductivity [W/(m K)]')]:
        twin=ax.twinx();line(ax,z,f[left][idx],left,'#bd2525');line(twin,z,f[right][idx],right,'#2459aa')
        ax.set_ylabel(lab1,color='#bd2525');twin.set_ylabel(lab2,color='#2459aa')
        ax.set_ylim(0,1.15*max(f[left][idx]));twin.set_ylim(0,1.15*max(f[right][idx]))
    for ax,letter in zip(axes.flat,'abcd'):
        ax.set_xlim(window);ax.set_title(f'({letter})',loc='left')
    finish(fig,number,f't = 1 microsecond; 320 cells; nearest-axis r = {r*1000:.3f} mm. Markers are cells; property y-ranges adapted.')

xyz,f,t,idx,r=cases['air-100'];z=xyz[idx,2]
fig,axes=plt.subplots(2,1,figsize=(7,8));fig.subplots_adjust(top=.89,bottom=.13,left=.14,right=.83,hspace=.35)
twin=axes[0].twinx();line(axes[0],z,f['T'][idx],'T','#bd2525');line(twin,z,f['rho'][idx],'rho','#2459aa')
axes[0].set_ylabel('Temperature [K]',color='#bd2525');twin.set_ylabel('Density [kg/m³]',color='#2459aa');axes[0].set_ylim(0,3000);twin.set_ylim(bottom=0)
for n,color in [('CH4','#242424'),('O2','#b32424'),('CO2','#2278a5'),('H2O','#2a8033')]:line(axes[1],z,f[n][idx],n,color)
axes[1].set_ylabel('Mass fraction');axes[1].set_ylim(0,1);axes[1].legend(fontsize=9)
for ax,letter in zip(axes,'ab'):ax.set_xlim(.0105,.012);ax.set_title(f'({letter})',loc='left')
finish(fig,11,f't = 1 microsecond; nearest-axis r = {r*1000:.3f} mm; only 3 cell centres in this window.')

fig,axes=plt.subplots(2,1,figsize=(8,9));fig.subplots_adjust(top=.90,bottom=.12,left=.12,right=.86,hspace=.35)
for ax,name,length in zip(axes,['oxy-1','oxy-200'],[.02,.005]):
    xyz,f,t,idx,r=cases[name]
    rr=np.unique(np.round(np.hypot(xyz[:,0],xyz[:,1]),12));zz=np.unique(np.round(xyz[:,2],12))
    order=np.lexsort((xyz[:,2],np.round(np.hypot(xyz[:,0],xyz[:,1]),12)))
    temp=f['T'][order].reshape(len(rr),len(zz))
    ue=f['U'][order,2].reshape(len(rr),len(zz));ve=f['U'][order,0].reshape(len(rr),len(zz))
    mesh=ax.pcolormesh(np.linspace(0,length,len(zz)+1),np.linspace(0,length,len(rr)+1),temp,cmap='turbo',vmin=300,vmax=3500,shading='flat')
    # Interpolate radial cell-centre velocities only to satisfy streamplot's uniform-grid requirement.
    grid=np.linspace(rr[0],rr[-1],len(rr))
    uu=np.stack([np.interp(grid,rr,ue[:,j]) for j in range(len(zz))],axis=1)
    vv=np.stack([np.interp(grid,rr,ve[:,j]) for j in range(len(zz))],axis=1)
    ax.streamplot(zz,grid,uu,vv,color='white',density=.7,linewidth=.6,arrowsize=.6)
    ax.set(xlim=(0,length),ylim=(0,length),xlabel='Axial distance z [m]',ylabel='Radius r [m]',title=name+'; t = 1 microsecond')
    fig.colorbar(mesh,ax=ax,label='Temperature [K]')
finish(fig,8,'8 radial x 40 axial cells. Nearly uniform hot initialization; streamlines are startup velocity only.')
print('Rendered four startup comparison figures; saved sampled profiles.')
