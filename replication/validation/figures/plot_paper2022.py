"""Render actual counterflow fields at 2022 paper dimensions and visual conventions."""
import json
import os
import sys
from pathlib import Path
import numpy as np
from foam_fields import read_case
root=Path(sys.argv[1]).resolve(strict=True)
os.environ['MPLCONFIGDIR']=str(root/'cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import AutoMinorLocator,MaxNLocator,FormatStrFormatter
font=Path('C:/Windows/Fonts/times.ttf')
if font.exists():
    for path in font.parent.glob('times*.ttf'):font_manager.fontManager.addfont(str(path))
family='Times New Roman' if font.exists() else 'DejaVu Serif'
plt.rcParams.update({'font.family':family,'font.size':5.5,'axes.labelsize':6.5,'axes.labelpad':1.5,'xtick.major.pad':1.5,'ytick.major.pad':1.5,'axes.labelweight':'bold',
 'axes.linewidth':.5,'xtick.direction':'in','ytick.direction':'in','xtick.major.size':3,'ytick.major.size':3,
 'xtick.major.width':.5,'ytick.major.width':.5,'xtick.minor.size':1.5,'ytick.minor.size':1.5,
 'lines.linewidth':.8,'mathtext.fontset':'stix','axes.formatter.useoffset':False})
out=root/'output/figure-comparison-20261017'
manifest={'status':'STARTUP ONLY - NOT REPLICATED','cases':{name:f'state/flame-pilots-20261017/jobs/{job}/{name}' for name,job in [('oxy-1',124660430),('oxy-200',124660583),('air-100',124660669)]}}
if len(sys.argv)>2:manifest=json.loads(Path(sys.argv[2]).read_text())
if not manifest.get('status'):raise ValueError('Explicit scientific status required')
cases={}
for name,relative in manifest['cases'].items():
    path=(root/relative).resolve(strict=True)
    if not path.is_relative_to(root):raise ValueError('Case escapes project root')
    xyz,fields,time=read_case(path);radial=np.hypot(xyz[:,0],xyz[:,1])
    indices=np.flatnonzero(np.isclose(radial,radial.min(),rtol=0,atol=1e-9));indices=indices[np.argsort(xyz[indices,2])]
    cases[name]=(xyz,fields,time,indices,radial)
inventory={r['id']:r for r in json.loads((out/'inventory.json').read_text())}
record={}

def figure(number):
    item=inventory[f'2022-fig{number:02}'];x0,y0,x1,y1=item['crop']
    return plt.figure(figsize=((x1-x0)/72,(y1-y0)/72))

def setup(ax,xlim,ylim,xlabel='z[m]',ylabel=''):
    ax.set(xlim=xlim,ylim=ylim,xlabel=xlabel,ylabel=ylabel)
    ax.xaxis.set_minor_locator(AutoMinorLocator());ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.xaxis.set_major_locator(MaxNLocator(4));ax.yaxis.set_major_locator(MaxNLocator(5))

def draw(ax,x,y,colour='red',label=None):
    ax.plot(x,y,'--',color=colour,label=label)
    visible=(x>=ax.get_xlim()[0])&(x<=ax.get_xlim()[1]);limits=ax.get_ylim()
    clipped=int(np.sum(visible&((y<limits[0])|(y>limits[1]))))
    if clipped:ax.text(.02,.03,f'{clipped} samples outside y-range',transform=ax.transAxes,fontsize=5,color='#8a3a20')
    return clipped

def save(fig,number,time,r):
    fig.savefig(out/f'plots/2022-fig{number:02}.png',dpi=360)
    fig.savefig(out/f'plots/2022-fig{number:02}.svg')
    record[str(number)]={'size_inches':list(fig.get_size_inches()),'status':manifest['status'],'time_s':time,'nearest_axis_r_m':r,'font':family}
    plt.close(fig)

for name,number,xlim,ohscale in [('oxy-1',9,(.003,.018),100),('oxy-200',10,(.002,.0035),500)]:
    xyz,f,t,idx,radial=cases[name];z=xyz[idx,2];fig=figure(number)
    positions=[(.145,.555,.307,.4),(.555,.555,.307,.4),(.145,.06,.307,.4),(.555,.06,.307,.4)]
    axes=[fig.add_axes(p) for p in positions];a,b,c,d=axes
    setup(a,xlim,(250,2100 if number==9 else 2400),ylabel='Temperature [K]');draw(a,z,f['T'][idx])
    a.set_yticks([500,1000,1500,2000]);a.text(.04,.90,'1 atm' if number==9 else '200 atm',transform=a.transAxes,fontweight='bold',fontsize=10)
    a.text(.03,.55,manifest['status']+f'\nt = {t:g} s',transform=a.transAxes,fontsize=5,color='#943321')
    setup(b,xlim,(-.02,1.02),ylabel='Mass Fraction');b.set_yticks(np.arange(0,1.01,.2))
    for n,col in [('CH4','black'),('O2','#0080ff'),('CO2','#00bcbc'),('H2O','#00ba00'),('OH','#ff00bc')]:
        draw(b,z,f[n][idx]*(ohscale if n=='OH' else 1),col,label=f'OHx{ohscale}' if n=='OH' else n)
    b.legend(loc='center right',fontsize=5,frameon=False)
    settings=[(c,'rho','Cp',(.19,.71) if number==9 else (35,165),(1100,2750) if number==9 else (1100,3600),r'Density [kg/m$^3$]',r'c$_p$[J/kg-K]'),
              (d,'mu','kappa',(0,6.5e-5) if number==9 else (0,7.5e-5),(.03,.145) if number==9 else (.055,.20),'Viscosity [kg/m-s]','Thermal Conductivity [W/m-K]')]
    for ax,left,right,lim1,lim2,label1,label2 in settings:
        setup(ax,xlim,lim1,ylabel=label1);tw=ax.twinx();setup(tw,xlim,lim2,xlabel='',ylabel=label2)
        draw(ax,z,f[left][idx]);draw(tw,z,f[right][idx])
        if left=='mu':ax.yaxis.set_major_formatter(FormatStrFormatter('%.0E'))
    for ax,letter in zip(axes,'abcd'):
        ax.set_xticks([.005,.01,.015] if number==9 else [.002,.0025,.003,.0035]);ax.text(-.13,1.0,letter+')',transform=ax.transAxes,fontsize=8,fontweight='bold')
    save(fig,number,t,float(radial.min()))

xyz,f,t,idx,radial=cases['air-100'];z=xyz[idx,2];fig=figure(11)
a=fig.add_axes((.17,.55,.66,.40));b=fig.add_axes((.17,.055,.66,.40))
setup(a,(.0105,.012),(200,2300),ylabel='Temperature [K]');tw=a.twinx();setup(tw,(.0105,.012),(10,120),xlabel='',ylabel=r'Density [kg/m$^3$]')
draw(a,z,f['T'][idx]);draw(tw,z,f['rho'][idx]);a.text(.03,.08,manifest['status']+f'\nt = {t:g} s',transform=a.transAxes,fontsize=5,color='#943321')
setup(b,(.0105,.012),(-.02,1.02),ylabel='Mass Fraction')
for n in ['CH4','O2','CO2','H2O']:draw(b,z,f[n][idx],label=n)
b.legend(fontsize=5,frameon=False)
for ax,letter in [(a,'a'),(b,'b')]:ax.text(-.13,1,letter+')',transform=ax.transAxes,fontsize=10,fontweight='bold')
save(fig,11,t,float(radial.min()))

fig=figure(8)
for index,(name,length,upper) in enumerate([('oxy-1',.02,2000),('oxy-200',.005,2400)]):
    xyz,f,t,idx,radial=cases[name];rr=np.unique(np.round(radial,12));zz=np.unique(np.round(xyz[:,2],12))
    order=np.lexsort((xyz[:,2],np.round(radial,12)));shape=(len(rr),len(zz))
    temp=f['T'][order].reshape(shape).T
    ax=fig.add_axes((.27,.55-index*.49,.51,.375))
    mesh=ax.pcolormesh(np.linspace(0,length,len(rr)+1),np.linspace(0,length,len(zz)+1),temp,cmap='hot',vmin=200,vmax=upper,shading='flat')
    rg=np.linspace(rr[0],rr[-1],len(rr))
    ur=f['U'][order,0].reshape(shape);uz=f['U'][order,2].reshape(shape)
    ur=np.stack([np.interp(rg,rr,ur[:,j]) for j in range(len(zz))]);uz=np.stack([np.interp(rg,rr,uz[:,j]) for j in range(len(zz))])
    ax.streamplot(rg,zz,ur,uz,color='#a1eded',density=.7,linewidth=.4,arrowsize=.5)
    setup(ax,(0,length),(0,length),xlabel='r [m]',ylabel='z [m]')
    cb=fig.add_axes((.45,.955-index*.49,.33,.025));fig.colorbar(mesh,cax=cb,orientation='horizontal',ticks=list(range(200,upper,400)))
    cb.tick_params(labelsize=5);fig.text(.19,.955-index*.49,('a)' if index==0 else 'b)')+'     T [K]',fontsize=8,fontweight='bold')
fig.text(.52,.085,manifest['status'],ha='center',fontsize=4,color='#943321',bbox={'facecolor':'white','alpha':.8,'edgecolor':'none','pad':1})
save(fig,8,t,None)
(out/'data/paper-style-provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print('Rendered Figures 8-11 at paper crop dimensions, retaining scientific status.')
