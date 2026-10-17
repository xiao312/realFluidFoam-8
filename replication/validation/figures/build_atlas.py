"""Build a local, source-attributed atlas for every numbered paper figure."""
import html
import json
import sys
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
root=Path(sys.argv[1]).resolve(strict=True)
pdf_name=sys.argv[2] if len(sys.argv)>2 else 'realfluidfoam-figure-atlas.pdf'
if Path(pdf_name).name != pdf_name or not pdf_name.endswith('.pdf'):
    raise ValueError('PDF output must be a local basename ending in .pdf')
out=root/'output/figure-comparison-20261017'
items=json.loads((out/'inventory.json').read_text())
assert len(items)==27 and len({i['id'] for i in items})==27
summary=[
'All 27 numbered figures are accounted for: 2 property comparisons, 4 startup diagnostics, 8 unavailable numerical results, 12 diagrams, and 1 reference property map.',
'Methane (2022 Figure 6): the OF8 SRK values closely overlay the digitized published curves. Across 19 resolvable pressure/property series, RMS differences are 0.013-0.355%. This is approximate vector-curve comparison, not an acceptance tolerance. The 1-atm density curve is too compressed on the printed scale to score; the clipped Cp peak is excluded.',
'Nitrogen (2025 Figure 6): 901 exact states per EOS at 3.98 MPa were computed in job 124662568. Density RMS deviations from current NIST are 2.85% (SRK) and 3.28% (PR). PR Cp RMS deviation is 4.45%, with a 28.87% maximum near 129.75 K. These are model-versus-reference errors, not measured errors against digitized 2025 curves.',
'The independent enthalpy-to-temperature inversion check still fails the strict 1e-6 relative criterion: methane 185/225 SRK and 208/225 PR; nitrogen 873/901 SRK and 901/901 PR. Exact-state property evaluations are separately restored and finite. No solver physics was changed.',
'Counterflow (2022 Figures 8-11): only 1 microsecond of startup exists on 320 cells. Profiles are nearly uniform hot initial conditions, not steady flames. Nearest-axis samples are at r=1.665 mm (1/100 atm) or 0.416 mm (200 atm), not r=0. A convergence campaign and mesh refinement remain necessary.',
'Premixed flame speed and all 2025 LES comparisons lack the necessary developed/time-averaged data. Their source figures are included with explicit missing-result statements. Schematics are implementation context, not numerical validation.',
'Provenance: unchanged solver source 48506de20ce67f35279c5347b09dcd86865a4c39; qualified build b1153ea9c64b9abf55f7be6c488549024c081279. Methane job 124660240; counterflow jobs 124660430/124660583/124660669; nitrogen input source 58cee1b4818ffaa4bdb5cadb0f590047db78263d. Source-PDF hashes, digitization notes and quantitative data are in the companion bundle.',
'Source figure crops are reproduced from the two owner-supplied papers for this private comparison. Original data/figures are not our simulation outputs. No paper image or extracted reference curve is published in the Git repository.'
]
labels={'property':'PROPERTY COMPARISON','startup':'STARTUP ONLY - NOT REPLICATED','missing':'RESULT UNAVAILABLE','diagram':'SOURCE DIAGRAM','context':'SOURCE CONTEXT MAP'}
provenance_path=out/'data/paper-style-provenance.json'
if provenance_path.exists():
    provenance=json.loads(provenance_path.read_text())
    if 'cases' in provenance:
        labels['developing']='DEVELOPING - NOT CONVERGED'
        details=[]
        for name,value in provenance['cases'].items():
            details.append(f"{name}: {value['cells']} cells, t={value['time_s']:g} s, nearest-axis r={value['nearest_axis_r_m']*1000:.4g} mm")
        summary[0]=summary[0].replace('4 startup diagnostics','4 developing-flow diagnostics')
        summary[4]='Counterflow (2022 Figures 8-11): '+ '; '.join(details)+'. These developing fields do not establish temporal or grid convergence. Curves retain the paper axes; out-of-range samples are marked.'
        summary[6]=summary[6].replace('counterflow jobs','initial counterflow jobs')
        summary[6]+=' Current counterflow case paths and plotting inputs are recorded in data/paper-style-provenance.json.'
        for item in items:
            if item['id'] not in ('2022-fig08','2022-fig09','2022-fig10','2022-fig11'):continue
            names={'2022-fig08':['oxy-1','oxy-200'],'2022-fig09':['oxy-1'],'2022-fig10':['oxy-200'],'2022-fig11':['air-100']}[item['id']]
            item['status']='developing'
            item['qualification']='; '.join(details[list(provenance['cases']).index(name)] for name in names)+'. Developing flow only; no steady-flame replication claimed.'
        if provenance.get('notes'):summary.insert(5,' '.join(provenance['notes']))
style=ParagraphStyle('body',fontName='Helvetica',fontSize=12,leading=18,textColor='#26313b')
width,height=landscape(A3)
pdf=canvas.Canvas(str(out/pdf_name),pagesize=(width,height))
pdf.setTitle('realFluidFoam - comparison of all 27 paper figures')
pdf.setAuthor('realFluidFoam replication project')
def para(text,x,y,w):
    p=Paragraph(html.escape(text),style);_,h=p.wrap(w,height);p.drawOn(pdf,x,y-h);return y-h-14

def base(title,page):
    pdf.setFillColorRGB(.09,.16,.23);pdf.setFont('Helvetica-Bold',21);pdf.drawString(40,height-42,title)
    pdf.setFont('Helvetica',10);pdf.drawString(40,22,'realFluidFoam replication | 2026-10-17 | private source comparison')
    pdf.drawRightString(width-40,22,str(page))

def picture(path,x,y,w,h,max_scale=None):
    img=ImageReader(str(path));iw,ih=img.getSize();scale=min(w/iw,h/ih)
    if max_scale is not None: scale=min(scale,max_scale)
    pdf.drawImage(img,x+(w-iw*scale)/2,y+(h-ih*scale)/2,width=iw*scale,height=ih*scale,mask='auto')

base('Paper figure comparison: current evidence',1)
y=height-85
for text in summary:y=para(text,45,y,width-90)
pdf.showPage()
sections=[]
for number,item in enumerate(items,2):
    ident=item['id'];original=out/f'originals/{ident}.png';plot=out/f'plots/{ident}.png'
    caption=out/f'captions/{ident}.png'
    assert caption.exists()
    assert original.exists()
    if item['status'] in ('startup','property','developing'):assert plot.exists()
    title=f"{item['year']} Figure {item['figure']} | {item['title']}"
    base(title,number)
    para(labels[item['status']]+' - '+item['qualification'],40,height-65,width-80)
    pdf.setFont('Helvetica-Bold',12);pdf.drawString(45,height-135,'Published figure (source PDF page '+str(item['page'])+')')
    if plot.exists():
        pdf.drawString(width/2+15,height-135,'Our calculations / diagnostics')
        picture(original,40,180,width/2-60,height-330)
        picture(plot,width/2+10,180,width/2-50,height-330)
        picture(caption,40,60,width/2-60,100,max_scale=.45)
        para('Our result: '+item['qualification'],width/2+15,145,width/2-65)
    else:
        picture(original,40,190,width*.68-40,height-340)
        picture(caption,40,55,width*.68-40,115,max_scale=.45)
        para(item['qualification'],width*.71,height-190,width*.25)
        para('No independently reproduced result is claimed for this figure.',width*.71,height-295,width*.25)
    pdf.showPage()
    images=f'<figure><figcaption>Published figure - source page {item["page"]}</figcaption><a href="originals/{ident}.png"><img src="originals/{ident}.png" alt="Published {ident}"></a><figcaption><span>Original paper caption (verbatim):</span><a href="captions/{ident}.png"><img class="caption" src="captions/{ident}.png" alt="Original caption for {ident}"></a></figcaption></figure>'
    if plot.exists():images+=f'<figure><figcaption>Our result - <a href="plots/{ident}.svg">SVG</a></figcaption><a href="plots/{ident}.png"><img src="plots/{ident}.png" alt="Our {ident}"></a><figcaption>Our result: {html.escape(item["qualification"])}</figcaption></figure>'
    sections.append(f'<section id="{ident}" data-status="{item["status"]}"><h2>{html.escape(title)}</h2><p class="status">{labels[item["status"]]}</p><p>{html.escape(item["qualification"])}</p><div class="pair">{images}</div></section>')
pdf.save()
nav=' '.join(f'<a href="#{i["id"]}">{i["year"]}/{i["figure"]}</a>' for i in items)
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>realFluidFoam figure comparison</title><style>body{font:16px/1.6 system-ui;color:#23313d;background:#f3f5f6;margin:0}main{max-width:1600px;margin:auto;padding:32px}section,header{background:white;padding:28px;margin:20px 0;border:1px solid #d6dde2;border-radius:8px}h1,h2{line-height:1.25}.pair{display:flex;gap:20px;align-items:start}figure{flex:1;min-width:0;margin:0}img{width:100%;height:auto}figcaption{padding:12px 0;font-size:14px}.caption{display:block;margin-top:8px}a{color:#175e96}nav a{display:inline-block;padding:5px}.status{font-weight:bold;color:#98512b}select{padding:8px}@media(max-width:900px){.pair{display:block}figure{margin-bottom:24px}}</style><main><header><h1>All 27 paper figures: comparison atlas</h1>'''
page+=''.join('<p>'+html.escape(p)+'</p>' for p in summary)
page+='<p><a href="realfluidfoam-figure-atlas.pdf">Download PDF atlas</a> | <a href="data/methane-paper-curve-errors.json">Methane metrics</a> | <a href="data/nitrogen-nist-errors.json">Nitrogen metrics</a> | <a href="source-provenance.json">Source provenance</a></p><nav>'+nav+'</nav><label>Show: <select id="filter"><option value="all">All figures</option>'+''.join(f'<option value="{k}">{v}</option>' for k,v in labels.items())+'</select></label></header>'
page+=''.join(sections)+'''</main><script>document.querySelector('#filter').onchange=e=>document.querySelectorAll('section').forEach(s=>s.hidden=e.target.value!=='all'&&s.dataset.status!==e.target.value);</script></html>'''
(out/'index.html').write_text(page.replace('realfluidfoam-figure-atlas.pdf',pdf_name),encoding='utf-8')
(out/'summary.json').write_text(json.dumps({'date':'2026-10-17','figures':27,'summary':summary},indent=2)+'\n')
print('Created 28-page PDF and offline HTML atlas.')
