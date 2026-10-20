"""Original-scale Liang Figs 1/2, with computed curves overlaid on the same axes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

PAPER_SHA='24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe'
GREEN=(0,.48,.27); PURPLE=(.60,.1,.65); BLUE=(0,.4,.75); ORANGE=(.75,.35,0)
FIG1=(48,53,240,384); CAP1=(48,394,240,424)
FIG2=(263,53,456,210); CAP2=(263,219,456,239)
CALIBRATION_PATH=Path(__file__).with_name('figure1-calibration.json')
CALIBRATION=json.loads(CALIBRATION_PATH.read_text(encoding='utf-8'))


def figure1_point(quantity, temperature, value):
    """Map physical coordinates through the independently measured source pixels."""
    rect=CALIBRATION['image_rect_points'];size=CALIBRATION['image_size_px']
    coords=[]
    for i,v in enumerate((temperature,value)):
        mapping=CALIBRATION['calibration'][quantity+('_x' if i==0 else '_y')]
        pixel=(v-mapping['value_intercept'])/mapping['value_per_pixel']
        coords.append(rect[i]+pixel*(rect[i+2]-rect[i])/size[i])
    return tuple(coords)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path,delimiter=','):
    with path.open() as f:return list(csv.DictReader(f,delimiter=delimiter))


def paper_critical_phi1(page):
    """Read source vector curves, preserving axis-calibration uncertainty."""
    curves={('H2','Tc'):[],('H2','Pc'):[],('CH4','Tc'):[],('CH4','Pc'):[]}
    for drawing in page.get_drawings():
        r=drawing['rect'];color=drawing['color']
        if drawing['fill'] is not None or color is None:continue
        quantity='Pc' if color[0]>.5 and color[1]<.1 else 'Tc'
        if len(drawing['items'])==12 and r.width>100:
            fuel='H2'
        elif r.x0>=282.7 and r.x1<=434.1 and r.width>3 and r.height<1 and (
            quantity=='Tc' and 77<r.y0<94 or quantity=='Pc' and 97<r.y0<114):
            fuel='CH4'
        else:continue
        for item in drawing['items']:
            if item[0]=='l':curves[fuel,quantity].extend([(p.x,p.y) for p in item[1:]])
    target=282.737+.4*(434.058-282.737)/1.4;result={}
    for (fuel,quantity),values in curves.items():
        points=sorted(set(values));left=max(p for p in points if p[0]<=target)
        right=min(p for p in points if p[0]>=target)
        y=left[1]+(target-left[0])/(right[0]-left[0])*(right[1]-left[1])
        value=60+(194.121-y)*100/(194.121-56.036) if quantity=='Tc' else 10+(188.808-y)*50/(188.808-56.037)
        result.setdefault(fuel,{})[quantity+'_K' if quantity=='Tc' else quantity+'_atm']=value
    return dict(phi=1,values=result,estimated_calibration_uncertainty={'Tc_K':.1,'Pc_atm':.05},
                method='Source PDF vector paths with calibrated dual axes; not author raw data')


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
    def calibrated_point(quantity,t,value):
        x,y=figure1_point(quantity,t,value)
        return ox+x,oy+y
    a=lambda t,r:calibrated_point('density',t,r)
    b=lambda t,k:calibrated_point('conductivity',t,k)
    curve(page,[(float(r['T_K']),float(r['rho_kg_m3'])) for r in oxygen if 225<=float(r['T_K'])<=1000],a,GREEN)
    curve(page,[(float(r['T_K']),float(r['kappa_W_m_K'])) for r in oxygen
                if float(r['T_K'])>=120 and .011<float(r['kappa_W_m_K'])<.149],b,GREEN)
    if 'kappa_mass_mapping_W_m_K' in oxygen[0]:
        curve(page,[(float(r['T_K']),float(r['kappa_mass_mapping_W_m_K'])) for r in oxygen
                    if float(r['T_K'])>=120 and .011<float(r['kappa_mass_mapping_W_m_K'])<.149],b,ORANGE,True,75)
    for r in nist:
        t=float(r['Temperature (K)'])
        if int(t)%100 or t<120:continue
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
    identity=dict(line.split('=',1) for line in (a.results.parent/'validation-inputs.txt').read_text().splitlines())
    run_identity='Property job %s | source %s | library build %s' % (
        a.results.parent.name.replace('job-',''),identity['source'][:7],identity['build_job'])
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
        page=doc.new_page(width=468,height=height+195)
        text(page,(18,12,450,35),'Liang Fig. %s: property-model comparison'%number,11)
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
            legend(page,246,bottom+38,'Mass-density mapping sensitivity',ORANGE,True)
            note=('Oxygen, 100 atm. Density calls the compiled SRK library. Conductivity uses the explicit\n'
                  'Ely-Hanley shape-factor variant and SRK volume; exact Liang variant remains unverified.\n'
                  'Orange: diagnostic mass-density mapping; this is not an established Liang input choice.\n'
                  'Below 200 K: NASA Cp is extrapolated. Black: paper data; blue: current NIST reference.')
        else:
            legend(page,246,bottom+8,'Computed Tc (green); Pc (purple)',GREEN)
            legend(page,246,bottom+23,'Dashed: CH4/air; solid: H2/air',PURPLE,True)
            note=('Fixed-composition SRK inflection, using repository species data and 21/79 molar O2/N2 air.\n'
                  'Original black/red curves are Liang Tc/Pc. Computed curves differ, especially pressure;\n'
                  'the implementation checks do not establish a paper replication. No constants were fitted.\n'
                  'This pseudocritical construction does not establish the full mixture critical locus.')
        text(page,(18,bottom+53,450,bottom+122),note+'\n'+run_identity,7.4)
        text(page,(18,bottom+127,450,bottom+140),'Source: Liang, Li & Law, PCI 37 (2019), 1733-1739. doi:10.1016/j.proci.2018.06.070',6.7)
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
        figure1_calibration_sha256=digest(CALIBRATION_PATH),
        input_sha256={p.name:digest(p) for p in a.results.glob('*.csv')},nist=manifest,
        source_page_index=2,figure_clips_pt=[FIG1,FIG2],caption_clips_pt=[CAP1,CAP2],
        checks=json.loads((a.results/'checks.json').read_text()),reference_errors=errors,
        paper_critical_phi1=paper_critical_phi1(source[2]),
        scientific_acceptance=False)
    record['outputs']={p.name:digest(p) for p in a.output.iterdir()}
    (a.output/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
