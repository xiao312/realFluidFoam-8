"""Original-scale Liang Figs 1/2, with computed curves overlaid on the same axes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

PAPER_SHA='24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe'
GREEN=(0,.48,.27); PURPLE=(.60,.1,.65); BLUE=(0,.4,.75)
FIG1=(48,53,240,384); CAP1=(48,394,240,424)
FIG2=(263,53,456,210); CAP2=(263,219,456,239)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path,delimiter=','):
    with path.open() as f:return list(csv.DictReader(f,delimiter=delimiter))


def text(page,box,content,size=8,color=(0,0,0)):
    if page.insert_textbox(box,content,fontname='helv',fontsize=size,color=color)<0:
        raise ValueError('Text overflow: '+content)


def curve(page,data,transform,color,dash=False,marker_every=50):
    import pymupdf as fitz
    points=[fitz.Point(*transform(x,y)) for x,y in data]
    if len(points)>1:page.draw_polyline(points,color=color,width=.7,dashes='[3 2] 0' if dash else None)
    for point in points[::marker_every]:page.draw_circle(point,1.25,color=color,fill=(1,1,1),width=.65)


def overlay1(page,origin,oxygen,nist):
    ox,oy=origin;ox-=FIG1[0];oy-=FIG1[1]
    # Calibration uses the embedded 775 x 1371-pixel image at 186 x 328.95 pt.
    # Density: 400 K at x108.9, 1000 K at230.6; rho0 at198.8, rho200 at73.2.
    a=lambda t,r:(ox+108.9+(t-400)*121.7/600,oy+198.8-r*125.6/200)
    b=lambda t,k:(ox+87.05+(t-200)*143.55/800,oy+359.2-(k-.02)*124.2/.12)
    curve(page,[(float(r['T_K']),float(r['rho_kg_m3'])) for r in oxygen if 225<=float(r['T_K'])<=1000],a,GREEN)
    curve(page,[(float(r['T_K']),float(r['kappa_W_m_K'])) for r in oxygen
                if .011<float(r['kappa_W_m_K'])<.149],b,GREEN)
    for r in nist:
        t=float(r['Temperature (K)'])
        if int(t)%100:continue
        for transform,value,valid in [(a,float(r['Density (kg/m3)']),t>=300),
                                      (b,float(r['Therm. Cond. (W/m*K)']),True)]:
            if valid:
                import pymupdf as fitz
                point=fitz.Point(*transform(t,value))
                page.draw_circle(point,1.4,color=BLUE,width=.7)


def overlay2(page,origin,critical):
    ox,oy=origin;ox-=FIG2[0];oy-=FIG2[1]
    t=lambda phi,v:(ox+282.737+(phi-.6)*(434.058-282.737)/1.4,
                    oy+194.121-(v-60)*(194.121-56.036)/100)
    p=lambda phi,v:(ox+282.737+(phi-.6)*(434.058-282.737)/1.4,
                    oy+188.808-(v-10)*(188.808-56.037)/50)
    for fuel in ['H2','CH4']:
        for key,transform,color in [('Tc_K',t,GREEN),('Pc_atm',p,PURPLE)]:
            data=[(float(r['phi']),float(r[key])) for r in critical if r['fuel']==fuel]
            curve(page,data,transform,color,fuel=='CH4',20)


def legend(page,x,y,label,color,dash=False):
    import pymupdf as fitz
    page.draw_line(fitz.Point(x,y+4),fitz.Point(x+15,y+4),color=color,width=.7,
                   dashes='[3 2] 0' if dash else None)
    page.draw_circle(fitz.Point(x+7,y+4),1.25,color=color,fill=(1,1,1),width=.65)
    text(page,(x+20,y,x+195,y+12),label,7,color)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply']);p.add_argument('paper',type=Path)
    p.add_argument('results',type=Path);p.add_argument('nist',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    if digest(a.paper)!=PAPER_SHA:raise ValueError('Uncalibrated paper PDF')
    if a.output.exists():raise ValueError('Output already exists')
    oxygen=read(a.results/'oxygen.csv');critical=read(a.results/'critical.csv')
    nist=read(a.nist/'oxygen-100atm.tsv','\t')
    manifest=json.loads((a.nist/'manifest.json').read_text())
    assert digest(a.nist/'oxygen-100atm.tsv')==manifest['sha256']
    print(json.dumps(dict(output=str(a.output),oxygen_states=len(oxygen),critical_states=len(critical))))
    if a.action=='plan':return
    import pymupdf as fitz
    a.output.mkdir(parents=True);source=fitz.open(a.paper);doc=fitz.open()
    for number,clip,caption,overlay in [(1,FIG1,CAP1,lambda p,o:overlay1(p,o,oxygen,nist)),
                                        (2,FIG2,CAP2,lambda p,o:overlay2(p,o,critical))]:
        width=clip[2]-clip[0];height=clip[3]-clip[1]
        page=doc.new_page(width=468,height=height+174)
        text(page,(18,12,450,29),'Liang Fig. %s: property-model comparison'%number,11)
        text(page,(18,35,222,49),'Original paper',8)
        text(page,(246,35,450,49),'Original + our computed data',8)
        for x in [18,246]:
            page.show_pdf_page(fitz.Rect(x,52,x+width,52+height),source,2,clip=fitz.Rect(clip))
        overlay(page,(246,52))
        capheight=caption[3]-caption[1];bottom=52+height
        page.show_pdf_page(fitz.Rect(18,bottom+8,18+width,bottom+8+capheight),source,2,clip=fitz.Rect(caption))
        if number==1:
            legend(page,246,bottom+8,'OpenFOAM SRK / new Ely-Hanley',GREEN)
            legend(page,246,bottom+23,'Current NIST (open blue circles)',BLUE)
            note=('Oxygen, 100 atm. Density calls the compiled SRK library. Conductivity uses the explicit\n'
                  'Ely-Hanley shape-factor variant and SRK volume; exact Liang variant remains unverified.\n'
                  'Below 200 K: NASA Cp is extrapolated and unqualified. Original black curves/triangles\n'
                  'are Liang model/reference data. New NIST evaluations are a separate reference.')
        else:
            legend(page,246,bottom+8,'Computed Tc (green); Pc (purple)',GREEN)
            legend(page,246,bottom+23,'Dashed: CH4/air; solid: H2/air',PURPLE,True)
            note=('Fixed-composition SRK inflection, using repository species data and 21/79 molar O2/N2 air.\n'
                  'Original black/red curves are Liang Tc/Pc. Computed curves differ, especially pressure;\n'
                  'the implementation checks do not establish a paper replication. No constants were fitted.\n'
                  'This pseudocritical construction does not establish the full mixture critical locus.')
        text(page,(18,bottom+48,450,bottom+101),note,7.4)
        text(page,(18,bottom+109,450,bottom+122),'Source: Liang, Li & Law, PCI 37 (2019), 1733-1739. doi:10.1016/j.proci.2018.06.070',6.7)
        page.get_pixmap(matrix=fitz.Matrix(3,3)).save(a.output/f'liang-fig{number}-comparison.png')
        single=fitz.open();s=single.new_page(width=width,height=height+35)
        s.show_pdf_page(fitz.Rect(0,0,width,height),source,2,clip=fitz.Rect(clip));overlay(s,(0,0))
        legend(s,2,height+5,'Computed: green'+(' / purple Pc' if number==2 else ''),GREEN)
        text(s,(2,height+20,width-2,height+33),'Original curves retained; agreement unqualified.',6.5)
        s.get_pixmap(matrix=fitz.Matrix(4,4)).save(a.output/f'liang-fig{number}-overlay.png')
    doc.save(a.output/'liang-figures-1-2.pdf',garbage=4,deflate=True)
    byT={float(r['T_K']):r for r in oxygen};errors={}
    for key,ref in [('rho_kg_m3','Density (kg/m3)'),('kappa_W_m_K','Therm. Cond. (W/m*K)')]:
        selected=[(float(byT[float(r['Temperature (K)'])][key])/float(r[ref])-1)*100
                  for r in nist if float(r['Temperature (K)'])>=300]
        errors[key]={'NIST_300_1000K_RMS_percent':(sum(v*v for v in selected)/len(selected))**.5,
                     'NIST_300_1000K_max_abs_percent':max(map(abs,selected))}
    record=dict(source_pdf_sha256=PAPER_SHA,plotter_sha256=digest(Path(__file__)),
        input_sha256={p.name:digest(p) for p in a.results.glob('*.csv')},nist=manifest,
        source_page_index=2,figure_clips_pt=[FIG1,FIG2],caption_clips_pt=[CAP1,CAP2],
        checks=json.loads((a.results/'checks.json').read_text()),reference_errors=errors,
        scientific_acceptance=False)
    record['outputs']={p.name:digest(p) for p in a.output.iterdir()}
    (a.output/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
