"""Compare stable GRI30 counterflow snapshots with approximate paper temperatures."""
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np
from foam_fields import read_decomposed

root, snapshot, out = (Path(v).resolve() for v in sys.argv[1:4])
assert snapshot.is_relative_to(root) and out.is_relative_to(root)
os.environ['MPLCONFIGDIR'] = str(root/'cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

for font in Path('C:/Windows/Fonts').glob('times*.ttf'):
    font_manager.fontManager.addfont(str(font))
plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'xtick.direction':'in','ytick.direction':'in'})
manifest = json.loads((snapshot/'snapshot.json').read_text())
atlas = root/'output/figure-comparison-20261017'
reference_path = atlas/'data/paper-2022-temperature-targets.csv'
reference = np.genfromtxt(reference_path, delimiter=',', names=True)
paper = json.loads((out/'data/paper-counterflow-curves.json').read_text())
summary = {'observed_at':manifest.get('updated_at',manifest['observed_at']), 'paper_curves_sha256':hashlib.sha256((out/'data/paper-counterflow-curves.json').read_bytes()).hexdigest(), 'status':'INTERIM; no mesh-convergence acceptance',
           'source_revision':'b15fb0db8213e6a5243c0f55691080195276253e',
           'solver':'upstream realFluidReactingFoam, qualified build 124657926',
           'reference_sha256':hashlib.sha256(reference_path.read_bytes()).hexdigest(), 'cases':{}}
fig, axes = plt.subplots(1,3,figsize=(12,3.8),constrained_layout=True)
for ax, (key, number) in zip(axes, [('oxy-1',9),('oxy-200',10),('air-100',11)]):
    meta = manifest['cases'][key]; case = snapshot/meta['case']; states=[]
    for time in meta['times']:
        xyz, fields, _ = read_decomposed(case,time)
        states.append(fields)
    r = np.hypot(xyz[:,0],xyz[:,1]); idx=np.flatnonzero(np.isclose(r,r.min(),atol=1e-9,rtol=0))
    idx=idx[np.argsort(xyz[idx,2])]; z=xyz[idx,2]; fields=states[-1]
    selected=reference[reference['figure']==number]
    order=np.argsort(selected['z_m']); zz=selected['z_m'][order]; tt=selected['T_K'][order]
    zz, unique=np.unique(zz,return_index=True);tt=tt[unique]
    visible=(z>=zz.min())&(z<=zz.max()); target=np.interp(z[visible],zz,tt)
    i=int(np.argmax(fields['T'][idx])); j=int(np.argmax(tt))
    row={'job':meta['job'],'time_s':float(meta['times'][-1]),'cells':len(xyz),'nearest_axis_radius_m':float(r.min()),
         'sampled_peak_T_K':float(fields['T'][idx][i]),'sampled_peak_z_m':float(z[i]),
         'paper_peak_T_K_approx':float(tt[j]),'paper_peak_z_m_approx':float(zz[j]),
         'temperature_RMS_difference_K_approx':float(np.sqrt(np.mean((fields['T'][idx][visible]-target)**2))),
         'qualification':'coarse GRI30 near-axis sample; no axial shifting; approximate paper-vector comparison'}
    row['peak_temperature_difference_percent_approx']=(row['sampled_peak_T_K']/row['paper_peak_T_K_approx']-1)*100
    row['peak_position_difference_um_approx']=(row['sampled_peak_z_m']-row['paper_peak_z_m_approx'])*1e6
    if len(states)>1:
        row['last_saved_interval_s']=float(meta['times'][-1])-float(meta['times'][-2])
        row['field_change']={n:{'RMS':float(np.sqrt(np.mean((states[-1][n]-states[-2][n])**2))),
            'max_abs':float(np.max(abs(states[-1][n]-states[-2][n])))} for n in ['T','CH4','OH','rho']}
    else:
        row['qualification']='prior successful 0.1 ms smoke; full job 124767672 failed at 0.1896 ms without a new checkpoint; not a developed flame'
    summary['cases'][key]=row
    for series,style,color,label in [('benchmark','-.','#222222','Benchmark (paper)'),('nguyen','--','#d62728','Nguyen (paper)')]:
        curve=next(c for c in paper['curves'] if c['figure']==number and c['field']=='T' and c['series']==series)
        ax.plot(np.array(curve['z_m'])*1000,curve['value'],style,color=color,lw=1,label=label)
    for n,(time,field) in enumerate(zip(meta['times'],states)):
        ax.plot(z*1000,field['T'][idx], '-' if n==len(states)-1 else ':', color='#165bbb' if n==len(states)-1 else '#888888',
                label=f'Saved {float(time)*1000:g} ms')
    ax.set(xlabel='Axial coordinate z [mm]',ylabel='Temperature [K]',title=key,xlim=(0,xyz[:,2].max()*1000),ylim=(250,2450))
    ax.legend(fontsize=7)
    if key=='air-100':ax.text(.03,.88,'SMOKE ONLY; FULL RUN FAILED',transform=ax.transAxes,fontsize=7,color='#a03020')
    names=['T','rho','Cp','mu','kappa','CH4','O2','CO2','H2O','OH']
    np.savetxt(out/'data'/f'{key}-near-axis.csv',np.column_stack([z,*[fields[n][idx] for n in names]]),
               delimiter=',',header=','.join(['z_m',*names]),comments='')
fig.suptitle('GRI30 counterflow: saved profiles versus paper temperature curves; no curve alignment')
fig.savefig(out/'plots/counterflow-temperature-comparison.png',dpi=220)
fig.savefig(out/'plots/counterflow-temperature-comparison.svg')
plt.close(fig)
(out/'data/summary.json').write_text(json.dumps(summary,indent=2)+'\n')

pdf=canvas.Canvas(str(out/'counterflow-paper-comparison.pdf'),pagesize=(1191,842))
style=ParagraphStyle('body',fontName='Helvetica',fontSize=10,leading=14)

def paragraph(text,x,y,w):
    p=Paragraph(text,style);_,h=p.wrap(w,750);p.drawOn(pdf,x,y-h)

def picture(path,x,y,w,h):
    image=ImageReader(str(path));iw,ih=image.getSize();scale=min(w/iw,h/ih)
    pdf.drawImage(image,x+(w-iw*scale)/2,y+(h-ih*scale)/2,width=iw*scale,height=ih*scale)

for number in [8,9,10,11]:
    pdf.setFont('Helvetica-Bold',18);pdf.drawString(35,805,f'2022 Figure {number}: latest retrieved counterflow comparison')
    if number==8:
        note=f"GRI30 oxyfuel snapshots: 1 atm at {summary['cases']['oxy-1']['time_s']*1000:g} ms and 200 atm at {summary['cases']['oxy-200']['time_s']*1000:g} ms; each uses 11,200 cells. Coarse-grid results, not accepted replication."
    else:
        key={9:'oxy-1',10:'oxy-200',11:'air-100'}[number];r=summary['cases'][key]
        note=f"Job {r['job']}; {r['time_s']*1000:g} ms; {r['cells']:,} cells; near-axis radius {r['nearest_axis_radius_m']*1000:.4f} mm. {r['qualification']}."
    paragraph(note,35,780,1120)
    picture(atlas/f'originals/2022-fig{number:02}.png',35,210,540,520)
    picture(out/f'plots/2022-fig{number:02}.png',610,210,540,520)
    picture(atlas/f'captions/2022-fig{number:02}.png',35,65,540,110)
    paragraph('Original paper crop and caption',35,200,540)
    paragraph('Current fields and both published line series (Figures 9-11)',610,200,540)
    paragraph('Upstream realFluidReactingFoam; case source b15fb0d; qualified library/solver build 124657926. These are not the new rfReactingFoam development counterflows. The larger paper-informed meshes have only passed mesh checks.',610,165,540)
    paragraph('Dash-dot: published benchmark; dashed: Nguyen; solid: our saved fields. Species retain quantity colours. Paper curves are approximate digitizations. Figure 8 remains a contour comparison. No mesh-convergence acceptance.',610,100,540)
    pdf.showPage()
pdf.setFont('Helvetica-Bold',18);pdf.drawString(35,805,'Temperature comparison and remaining limits')
picture(out/'plots/counterflow-temperature-comparison.png',35,385,1120,370)
for i,(key,row) in enumerate(summary['cases'].items()):
    line=f"{key}: sampled peak {row['sampled_peak_T_K']:.1f} K versus paper ~{row['paper_peak_T_K_approx']:.1f} K; peak-location difference {row['peak_position_difference_um_approx']:+.1f} micrometres."
    if 'field_change' in row:line+=f" Whole-field T RMS change over 0.5 ms: {row['field_change']['T']['RMS']:.5f} K."
    paragraph(line,35,345-i*45,1120)
paragraph('Both published series are approximate PDF line digitizations, not author tables. Figures 9/10 use OPPDIF; Figure 11 uses Juanos and Sirignano. Numerical peak/RMS comparisons above use Nguyen only. Partial reference curves are not extrapolated; no axial alignment was applied.',35,190,1120)
paragraph('These oxyfuel snapshots use the 11,200-cell tutorial mesh, much coarser than the paper-informed meshes. Air-100 remains failed: its displayed 0.1 ms smoke cannot be claimed as a steady counterflow result. All original data, hashes and checkpoints are retained.',35,140,1120)
pdf.save()
print(json.dumps(summary,indent=2))
