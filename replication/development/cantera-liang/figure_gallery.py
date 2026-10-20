"""Render the seven agreed Figure 8(a) comparisons from frozen evidence."""
import argparse,hashlib,json
from pathlib import Path
from plot import PAPER_SHA,COLORS,panel_coordinates

LABELS=['Ideal gas','SRK density','SRK enthalpy','Dense conductivity','Takahashi diffusion (Table 2)']

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply'])
    for name in ['paper','cantera','reference','cfd_audit','sweep_audit','output']:
        p.add_argument(name,type=Path)
    a=p.parse_args()
    hashes={n:hashlib.sha256(getattr(a,n).read_bytes()).hexdigest()
            for n in ['paper','cantera','reference','cfd_audit','sweep_audit']}
    if hashes['paper']!=PAPER_SHA:raise ValueError('Unexpected paper PDF')
    ct=json.loads(a.cantera.read_text(encoding='utf-8-sig'))
    ref=json.loads(a.reference.read_text())
    cfd=json.loads(a.cfd_audit.read_text());sweep=json.loads(a.sweep_audit.read_text())
    if ref['paper_sha256']!=PAPER_SHA or len(ct['results'])!=65:raise ValueError('Unexpected reference coverage')
    if a.output.exists():raise ValueError('Use a new output directory')
    print(json.dumps(dict(output=str(a.output.resolve()),pages=7,source_hashes=hashes)))
    if a.action=='plan':return
    import pymupdf as f
    a.output.mkdir(parents=True);source=f.open(a.paper);combined=f.open();manifest=[]
    latest={r['key']:r for r in cfd['cases']}
    energy=[dict(phi=r['phi'],speed_cm_s=r['markers']['T']['last_mean_cm_s'],
                 job=r['job'],time_us=r['latest_time_us'],state=r['state']) for r in sweep['cases']]
    def series(label,rows,color,marker='circle',connect=False):
        return dict(label=label,rows=rows,color=color,marker=marker,connect=connect)
    def point(key):
        r=latest[key]
        return [dict(phi=1.1,speed_cm_s=r['markers']['T']['last_mean_cm_s'],
                     job=r['job'],time_us=r['latest_time_us'],state=r['state'])]
    ours=[series('Energy-corrected solver',energy,(0,.3,.8),'circle',True),
          series('Native tracked solver',point('native300'),(.6,.2,.7),'square'),
          series('Cantera transport / native chemistry',point('transport'),(0,.55,.6),'square'),
          series('Cantera transport / CP chemistry',point('cp'),(.5,.3,.1),'square')]
    figures=[]
    figures.append(('cantera-overview','Cantera overview',[
        series('Cantera Case '+str(s)+': '+LABELS[s-1],[r for r in ct['results'] if r['stage']==s],COLORS[s-1],connect=True)
        for s in range(1,6)],False,None))
    figures.append(('openfoam-overview','Developed realFluidFoam solver overview',ours,False,None))
    for s in range(1,6):
        rows=[r for r in ref['rows'] if r['stage']==s]
        items=[series('Liang Case '+str(s)+' (digitized)',rows,(0,0,0),'line' if s in [1,5] else 'square',s in [1,5]),
               series('Cantera Case '+str(s),[r for r in ct['results'] if r['stage']==s],COLORS[s-1],connect=True)]
        if s==1:
            items+=ours+[series('Stock reactingFoam',point('stock'),(.8,0,.2),'square'),
                         series('DeepFlame dfLowMachFoam',point('deepflame'),(.9,.45,0),'square')]
        figures.append(('case-'+str(s),'Case '+str(s)+': '+LABELS[s-1],items,True,s))
    for name,title,items,clear,stage in figures:
        doc=f.open();page=doc.new_page(width=468,height=420)
        def text(rect,value,size=8,color=(0,0,0)):
            if page.insert_textbox(f.Rect(rect),value,fontsize=size,fontname='helv',color=color)<0:
                raise ValueError('Text overflow: '+value)
        text((18,10,450,30),'Liang Figure 8(a) | '+title,10)
        text((18,33,222,49),'Original paper',8)
        text((246,33,450,49),'Computed comparison',8)
        for x in [18,246]:page.show_pdf_page(f.Rect(x,50,x+204,225),source,5,clip=f.Rect(28,50,232,225))
        if clear:
            # Keep the original axis frame, labels and ticks. Remove all paper
            # series inside it so this panel contains only the selected case.
            page.draw_rect(f.Rect(246+25.4,50+5.4,246+193.5,50+158.8),color=None,fill=(1,1,1))
            page.draw_rect(f.Rect(246+25.4,50+5.4,246+193.5,50+158.8),color=(0,0,0),width=.65)
            for i in range(50,81):
                y=50+panel_coordinates(1,i/10)[1]
                page.draw_line(f.Point(271.4,y),f.Point(271.4+(3.5 if i%5==0 else 1.8),y),width=.5)
            for i in range(94,143,2):
                x=246+panel_coordinates(i/100,6)[0]
                page.draw_line(f.Point(x,208.8),f.Point(x,208.8-(3.5 if i%10==0 else 1.8)),width=.5)
            text((282,62,435,76),'Methane/Air 100 atm',8)
        plotted=[];excluded=[]
        for index,item in enumerate(items):
            rows=sorted(item['rows'],key=lambda r:r['phi']);points=[]
            for row in rows:
                if not .916<=row['phi']<=1.437:
                    excluded.append(dict(series=item['label'],**row));continue
                x,y=panel_coordinates(row['phi'],row['speed_cm_s']);pt=f.Point(246+x,50+y)
                if not f.Rect(246,50,450,225).contains(pt):raise ValueError('Point outside panel')
                points.append(pt)
            color=item['color']
            if item['connect'] and len(points)>1:
                page.draw_polyline(points,color=color,width=.65,
                    dashes=None if item['marker']=='line' else '[2 2] 0')
            def marker(pt):
                if item['marker']=='square':page.draw_rect(f.Rect(pt.x-1.4,pt.y-1.4,pt.x+1.4,pt.y+1.4),color=color,fill=(1,1,1),width=.65)
                elif item['marker']=='circle':page.draw_circle(pt,1.3,color=color,fill=(1,1,1),width=.65)
                else:page.draw_line(f.Point(pt.x-3,pt.y),f.Point(pt.x+3,pt.y),color=color,width=.8)
            if item['marker']!='line':
                for pt in points:marker(pt)
            y=234+index*12;marker(f.Point(251,y+4))
            text((260,y,450,y+13),item['label'],6.8,color)
            plotted.append(dict(label=item['label'],points=len(points),rows=rows))
        page.show_pdf_page(f.Rect(18,233,222,262),source,5,clip=f.Rect(28,424,232,453))
        note=('Original curves are unchanged in the left panel. Right: only the selected paper case, plus available calculations.'
              if clear else 'Original paper curves remain visible. New open symbols and dashed lines are our calculations.')
        text((18,270,222,318),note,7.4)
        if stage and stage>1:
            text((246,274,450,317),'OpenFOAM results pending: matching staged CFD models are not yet qualified. No CFD curve is inferred.',8)
        text((18,346,450,406),'Cantera: 13 conditions per case; Case 5 uses corrected Takahashi Table 2.\n'
             'CFD: latest valid temperature-front speed relative to gas; endpoints differ and are not steady-state acceptance.\n'
             'CFD capture: '+cfd['capture_utc']+'. Paper digitization uncertainty is retained in the reference JSON.\n'
             'Points outside the printed equivalence-ratio range are omitted and listed in the manifest.',7.3)
        doc.save(a.output/(name+'.pdf'));page.get_pixmap(matrix=f.Matrix(3,3)).save(a.output/(name+'.png'))
        combined.insert_pdf(doc);manifest.append(dict(name=name,series=plotted,excluded=excluded,stage=stage))
    assert len(combined)==7
    combined.save(a.output/'liang-figure8a-seven-comparisons.pdf')
    (a.output/'manifest.json').write_text(json.dumps(dict(input_hashes=hashes,
        plotter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        panel_size_pt=[204,175],figures=manifest,scientific_acceptance=False),indent=2)+'\n')

if __name__=='__main__':main()
