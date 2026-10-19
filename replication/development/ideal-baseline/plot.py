"""Compare computed speeds with approximate Liang Case-1 raster digitization."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def reference(image, output):
    import numpy as np
    from PIL import Image
    pixels=np.array(Image.open(image).convert('RGB'))
    if pixels.shape!=(1218,612,3):raise ValueError('Expected the recorded Fig.8 crop dimensions')
    # Pixel calibration in the supplied PDF crop: phi=1/1.4 ticks and SL=7.5/5.
    x1,x14,y75,y5=157.5,542.5,94.5,461.5
    anchors=np.array([[.95,258],[1,176],[1.05,120],[1.1,100],[1.15,116],
        [1.2,150],[1.25,185],[1.3,223],[1.35,261],[1.4,298]])
    points=[]
    for phi,guess in anchors:
        x=int(round(x1+(phi-1)*(x14-x1)/.4))
        # Use adjacent columns to reduce interference from Case-2 diamonds.
        samples=[]
        for column in [x-7,x-6,x+6,x+7]:
            center=np.interp(column,[x1+(q-1)*(x14-x1)/.4 for q in anchors[:,0]],anchors[:,1])
            lo,hi=max(0,int(center)-14),min(470,int(center)+15)
            candidates=np.where(np.max(pixels[lo:hi,column,:],axis=1)<95)[0]+lo
            if len(candidates):samples.append(float(np.median(candidates)))
        if len(samples)<2:raise ValueError('Unresolved black curve at phi='+str(phi))
        y=float(np.mean(samples))
        speed=7.5+(y75-y)*2.5/(y5-y75)
        points.append({'phi':float(phi),'speed_cm_s':speed,'image_uncertainty_cm_s':.03})
    with (output/'liang-ideal-digitized.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(points[0]));writer.writeheader();writer.writerows(points)
    (output/'digitization.json').write_text(json.dumps({'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
        'source':'Liang 2019 Fig.8(a), Case 1 black curve; not author numeric data',
        'calibration_pixels':{'phi1':x1,'phi1.4':x14,'speed7.5':y75,'speed5':y5},
        'estimated_reading_uncertainty_cm_s':.03,'points':points},indent=2)+'\n')
    return points,pixels


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('image',type=Path);p.add_argument('cantera',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--cfd',type=Path,help='JSON list with phi, speed_cm_s and label; absent means pending')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.ticker import MultipleLocator
    points,pixels=reference(a.image,a.output)
    ct=sorted(json.loads((a.cantera/'results.json').read_text()),key=lambda r:r['phi'])
    plt.rcParams.update({'font.family':'Arial','font.size':8,'axes.labelsize':8,'axes.linewidth':.8,
        'xtick.direction':'in','ytick.direction':'in','lines.linewidth':1.1,'legend.fontsize':7})
    fig,axes=plt.subplots(1,2,figsize=(8.16,4.0),gridspec_kw={'width_ratios':[1,1]})
    axes[0].imshow(pixels[:525]);axes[0].axis('off')
    axes[0].set_title('Liang et al., Fig. 8(a) — supplied paper',fontsize=8)
    ax=axes[1]
    ax.plot([r['phi'] for r in points],[r['speed_cm_s'] for r in points],'k-',label='Liang Case 1 (image, ±0.03 cm/s)')
    ax.plot([r['phi'] for r in ct],[r['speed_cm_s'] for r in ct],color='#2266bb',marker='o',
        markersize=3,markerfacecolor='white',label='Cantera 3.2, author GRI30 inputs')
    if a.cfd:
        cfd=json.loads(a.cfd.read_text())
        for label in dict.fromkeys(r['label'] for r in cfd):
            rows=sorted([r for r in cfd if r['label']==label],key=lambda r:r['phi'])
            ax.plot([r['phi'] for r in rows],[r['speed_cm_s'] for r in rows],'s--',markersize=3,label=label)
    else:
        ax.text(.04,.93,'Our CFD runs are active; converged speeds pending',transform=ax.transAxes,fontsize=7)
    ax.set(xlim=(.916,1.437),ylim=(4.92,8.03),xlabel='Equivalence Ratio',ylabel='Laminar Flame Speed (cm/s)')
    ax.xaxis.set_major_locator(MultipleLocator(.1));ax.xaxis.set_minor_locator(MultipleLocator(.02))
    ax.yaxis.set_major_locator(MultipleLocator(.5));ax.yaxis.set_minor_locator(MultipleLocator(.1))
    ax.tick_params(which='major',length=4);ax.tick_params(which='minor',length=2)
    ax.legend(loc='lower left',frameon=False)
    ax.set_title('Ideal gas — Methane/air, 100 atm, Tu = 298 K',fontsize=8)
    fig.subplots_adjust(left=.02,right=.99,bottom=.18,top=.90,wspace=.23)
    fig.text(.02,.055,'Liang: modified PREMIX. Cantera: steady FreeFlame, mixture-averaged transport, Soret off.\n'
        'Liang Tu is not stated in the supplied main article. Our solver uses Sutherland / kinetic transport.',fontsize=7)
    for extension in ['png','pdf','svg']:fig.savefig(a.output/('ideal-comparison.'+extension),dpi=220)
    plt.close(fig)
    # Preserve the paper's pixels, axes and typography; add only computed data.
    overlay=plt.figure(figsize=(6.12,5.9),dpi=100)
    paper=overlay.add_axes([0,65/590,1,525/590])
    paper.imshow(pixels[:525],extent=(0,612,525,0));paper.set_xlim(0,612);paper.set_ylim(525,0);paper.axis('off')
    to_x=lambda phi:157.5+(phi-1)*385/.4
    to_y=lambda speed:94.5+(7.5-speed)*367/2.5
    visible=[r for r in ct if .916<=r['phi']<=1.437]
    paper.plot([to_x(r['phi']) for r in visible],[to_y(r['speed_cm_s']) for r in visible],
        color='#00894c',marker='o',mfc='white',ms=3,lw=1.2,ls='--')
    overlay.text(.03,.075,'Green circles: Cantera, author GRI30, 298 K, ideal gas',fontsize=8,color='#00894c')
    if a.cfd:
        for label in dict.fromkeys(r['label'] for r in cfd):
            rows=sorted([r for r in cfd if r['label']==label and .916<=r['phi']<=1.437],key=lambda r:r['phi'])
            paper.plot([to_x(r['phi']) for r in rows],[to_y(r['speed_cm_s']) for r in rows],
                marker='s',ms=3,lw=1,ls='--',label=label)
        paper.legend(loc='upper center',bbox_to_anchor=(.5,-.08),frameon=False,fontsize=7)
    else:
        overlay.text(.03,.035,'Paper pixels retained. Our CFD runs are active; converged speeds pending.',fontsize=8)
    overlay.savefig(a.output/'ideal-paper-overlay.png',dpi=200)
    overlay.savefig(a.output/'ideal-paper-overlay.pdf')
    plt.close(overlay)
    comparisons=[]
    for row in ct:
        ref=next((r for r in points if abs(r['phi']-row['phi'])<1e-8),None)
        if ref:comparisons.append({'phi':row['phi'],'cantera_cm_s':row['speed_cm_s'],
            'liang_image_cm_s':ref['speed_cm_s'],'difference_cm_s':row['speed_cm_s']-ref['speed_cm_s']})
    (a.output/'comparison.json').write_text(json.dumps(comparisons,indent=2)+'\n')
    print(json.dumps(comparisons,indent=2))


if __name__=='__main__':main()
