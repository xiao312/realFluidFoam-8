"""Operator-only raster digitization. Upload its numeric outputs, never paper images."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import pymupdf


def main():
    p=argparse.ArgumentParser();p.add_argument('--pdf',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--qa-out',type=Path,required=True);a=p.parse_args()
    if a.out.exists() or a.qa_out.exists():raise ValueError('Use new output directories')
    a.out.mkdir(parents=True);a.qa_out.mkdir(parents=True);doc=pymupdf.open(a.pdf)
    images={i:Image.open(io.BytesIO(doc.extract_image(i)['image'])).convert('RGB') for i in [41,43,55,57]}
    refs=[];provenance=[];qa={i:im.copy() for i,im in images.items()}
    def extract(identifier,figure,quantity,xref,box,ylimits,rule,guide=None,radius=None,legend=None):
        rgb=np.array(images[xref]).astype(int);x0,y0,x1,y1=box
        xs=np.arange(rgb.shape[1]);ys=np.arange(rgb.shape[0]);xx,yy=np.meshgrid(xs,ys)
        mask=rule(rgb)&(xx>x0+1)&(xx<x1-1)&(yy>y0+1)&(yy<y1-1)
        if legend:
            left,top,right,bottom=legend
            mask&=~((xx>=left)&(xx<=right)&(yy>=top)&(yy<=bottom))
        if guide:
            expected=np.interp((xs-x0)/(x1-x0),[v[0] for v in guide],[v[1] for v in guide])
            value=ylimits[1]-(yy-y0)/(y1-y0)*(ylimits[1]-ylimits[0])
            mask&=abs(value-expected[None,:])<radius
        points=[];draw=ImageDraw.Draw(qa[xref])
        for x in range(x0+2,x1-1):
            selected=np.flatnonzero(mask[:,x])
            if not len(selected):continue
            y=float(np.median(selected));points.append([(x-x0)/(x1-x0),ylimits[1]-(y-y0)/(y1-y0)*(ylimits[1]-ylimits[0])])
            if x%7==0:draw.ellipse((x-2,y-2,x+2,y+2),fill='white',outline='black')
        if len(points)<40:raise ValueError(f'Too few reference samples: {identifier}: {len(points)}')
        refs.append({'id':identifier,'figure':figure,'quantity':quantity,'unit':'K' if quantity=='T' else 'mass fraction',
            'scale':4000 if quantity=='T' else (.35 if figure==2 else 1),
            'uncertainty_y_approx':(ylimits[1]-ylimits[0])/(y1-y0)*2,'points':points})
        with (a.out/(identifier+'.csv')).open('w',newline='') as handle:
            writer=csv.writer(handle);writer.writerow(['c' if figure==2 else 'f',quantity]);writer.writerows(points)
        provenance.append({'id':identifier,'xref':xref,'image_sha256':hashlib.sha256(doc.extract_image(xref)['image']).hexdigest(),
            'axis_box_pixels':box,'y_limits':ylimits,'samples':len(points),'guide':guide,'corridor_half_width':radius,
            'method':'Colour threshold and median row per column. A manually read corridor separates overlapping same-colour species. No simulation used.'})
    red=lambda v:(v[:,:,0]>170)&(v[:,:,1]<130)&(v[:,:,2]<130)
    blue=lambda v:(v[:,:,2]>180)&(v[:,:,0]<160)&(v[:,:,1]<160)&(abs(v[:,:,0]-v[:,:,1])<35)
    pink=lambda v:(v[:,:,0]>180)&(v[:,:,2]>150)&(v[:,:,1]<200)&(v[:,:,2]>v[:,:,1]+40)&(v[:,:,0]>v[:,:,1]+40)
    cyan=lambda v:(v[:,:,2]>150)&(v[:,:,0]<80)&(v[:,:,1]>85)&(v[:,:,1]<225)
    green=lambda v:(v[:,:,1]>100)&(v[:,:,1]>v[:,:,0]+50)&(v[:,:,1]>v[:,:,2]+50)
    black=lambda v:(v.max(axis=-1)<110)
    extract('fig1-T-burnt',1,'T',41,[127,6,757,582],[0,3800],red,legend=[430,10,630,120])
    guides={
      'CH4':[(0,0),(.35,0),(.4,.015),(.5,.16),(.6,.33),(.8,.66),(1,1)],
      'O2':[(0,1),(.05,.71),(.1,.42),(.15,.2),(.2,.06),(.25,.005),(.3,0),(1,0)],
      'CO2':[(0,0),(.05,.1),(.1,.22),(.15,.29),(.2,.28),(.25,.22),(.3,.14),(.4,.08),(.5,.085),(.6,.075),(.8,.04),(1,0)],
      'CO':[(0,0),(.1,0),(.15,.06),(.2,.16),(.25,.32),(.3,.47),(.35,.59),(.4,.61),(.5,.51),(.6,.41),(.8,.2),(1,0)],
      'H2O':[(0,0),(.05,.1),(.1,.2),(.15,.3),(.2,.38),(.25,.41),(.3,.37),(.35,.25),(.4,.19),(.5,.155),(.6,.12),(.8,.06),(1,0)],
      'OH':[(0,0),(.1,.02),(.15,.06),(.2,.073),(.25,.05),(.3,.005),(.35,0),(1,0)]}
    for name,rule in zip(guides,[red,blue,black,blue,green,pink]):
        extract('fig1-'+name+'-burnt',1,name,43,[66,11,519,424],[0,1],rule,guides[name],.045)
    # Native source images avoid errors introduced by the presentation crop/resizing.
    for quantity,xref,box,ylimits in [('T',55,[87,11,525,413],[0,4000]),('CO2',57,[76,12,508,413],[-.05,.35])]:
        for f,rule in zip([.1,.2,.4,.6],[cyan,blue,red,pink]):
            extract(f'fig2-{quantity}-f{f:g}',2,quantity,xref,box,ylimits,rule,legend=[box[0]+1,box[1]+1,box[0]+285,box[1]+143])
    for xref,image in qa.items():image.save(a.qa_out/f'digitization-{xref}.png')
    data={'schema':'sharma-digitized-curves/v1','paper':'Sharma et al., arXiv:2311.15034v1, Figures 1–2',
        'paper_sha256':hashlib.sha256(a.pdf.read_bytes()).hexdigest(),
        'score_contract':'Figure2 weight .8; Figure1 weight .2. Each curve equal weight within figure. Trapezoidal x weights. Missing prediction contributes one plus worst admissible squared normalized error. T bounds 0..6000 K; Y bounds -1e-8..1+1e-8. score=exp(-10*weightedNRMSE-2*(1-meanCoverage)).',
        'qualification':'Approximate raster digitization, about two-pixel uncertainty. No invented intermediate c labels. No scientific acceptance.',
        'curves':refs}
    (a.out/'curves.json').write_text(json.dumps(data,indent=2)+'\n')
    (a.out/'provenance.json').write_text(json.dumps({'curves':provenance,'images_uploaded':False},indent=2)+'\n')
    print(json.dumps({v['id']:len(v['points']) for v in refs},indent=2))


if __name__=='__main__':main()
