"""Place computed staged-model points on Liang's unchanged Figure 8(a) frame."""
import argparse
import hashlib
import json
from pathlib import Path

PAPER_SHA='24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe'
COLORS=[(0,.48,.27),(.6,.2,.7),(0,.55,.7),(.9,.45,0),(.45,.28,.1)]
LABELS=['1: Ideal gas','2: + SRK density','3: + SRK enthalpy','4: + Ely-Hanley conductivity','5: + Takahashi diffusion']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply'])
    for name in ['paper','results','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    if hashlib.sha256(a.paper.read_bytes()).hexdigest()!=PAPER_SHA:raise ValueError('Unexpected source PDF')
    data=json.loads(a.results.read_text(encoding='utf-8-sig'));rows=data['results']
    if a.output.exists():raise ValueError('Output exists')
    if not rows or any(not 1<=r['stage']<=5 or r['speed_cm_s']<=0 for r in rows):raise ValueError('Invalid results')
    print(json.dumps({'output':str(a.output.resolve()),'computed_points':len(rows),'panel_size_pt':[204,175]}))
    if a.action=='plan':return
    import pymupdf as f
    a.output.mkdir(parents=True);source=f.open(a.paper);doc=f.open();page=doc.new_page(width=468,height=385)
    def text(box,value,size=8,color=(0,0,0)):
        if page.insert_textbox(f.Rect(box),value,fontsize=size,fontname='helv',color=color)<0:raise ValueError('Text overflow')
    text((18,12,450,34),'Liang Fig. 8(a): staged methane/air flames at 100 atm',11)
    text((18,35,222,51),'Original paper',8)
    text((246,35,450,51),'Original frame + computed points',8)
    for x in [18,246]:page.show_pdf_page(f.Rect(x,52,x+204,227),source,5,clip=f.Rect(28,50,232,225))
    # The phi=1.44 endpoint is outside the printed axes. Preserve it in data,
    # and disclose its exclusion instead of drawing over the paper's border.
    plotted=[r for r in rows if .916<=r['phi']<=1.437]
    excluded=[r for r in rows if r not in plotted]
    for stage in range(1,6):
        group=sorted([r for r in plotted if r['stage']==stage],key=lambda r:r['phi'])
        points=[f.Point(246+(157.5+(r['phi']-1)*385/.4)/3,52+(94.5+(7.5-r['speed_cm_s'])*367/2.5)/3) for r in group]
        # Fail instead of silently clipping an unexpected model result.
        if any(not f.Rect(246,52,450,227).contains(pt) for pt in points):raise ValueError('Point outside original panel')
        color=COLORS[stage-1]
        if len(points)>1:page.draw_polyline(points,color=color,width=.7,dashes='[2 2] 0')
        for pt in points:page.draw_circle(pt,1.3,color=color,fill=(1,1,1),width=.65)
        y=236+(stage-1)*12
        page.draw_circle(f.Point(251,y+4),1.3,color=color,fill=(1,1,1),width=.65)
        text((260,y,450,y+14),LABELS[stage-1]+(' (pending)' if not group else ''),7,color)
    page.show_pdf_page(f.Rect(18,235,222,264),source,5,clip=f.Rect(28,424,232,453))
    text((18,273,222,305),'Original curves remain visible. New open circles and dashed lines are our calculations; lines only connect solved conditions.',7.3)
    text((18,309,450,370),'Cantera 3.2 custom SRK/transport adapters; author GRI30; Tu=298 K (assumed).\n'
         'Molar reference-density mapping; concentration-law kinetics; no Soret.\n'
         'Phi=1.44 is outside the printed axes; retained in the data, omitted here.\n'
         'Publication parameter identity and domain independence remain unqualified.',7.5)
    doc.save(a.output/'liang-staged-comparison.pdf',garbage=4,deflate=True)
    page.get_pixmap(matrix=f.Matrix(3,3)).save(a.output/'liang-staged-comparison.png')
    page.get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(242,32,454,300)).save(a.output/'liang-staged-overlay.png')
    manifest={'paper_sha256':PAPER_SHA,'results_sha256':hashlib.sha256(a.results.read_bytes()).hexdigest(),
              'plotter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results':rows,
              'panel_size_pt':[204,175],'excluded_outside_printed_phi_axis':excluded,
              'publication_agreement':'not established'}
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
