"""Extract approximate temperature targets from the 2022 vector flame figures."""
import csv,json,sys
from pathlib import Path
import pymupdf
pdf=Path(sys.argv[1]);out=Path(sys.argv[2]);d=pymupdf.open(pdf)
# Major-tick positions verified against the original plots. These are drawing
# coordinates, not recovered author tables. No simulation inputs depend on them.
calibrations={9:(11,111.789,272.970,.003,.018,167.369,69.521,500,2000),
              10:(11,113.017,272.467,.002,.0035,536.499,453.208,500,2000),
              11:(12,80.167,249.037,.0105,.012,173.053,82.866,500,2000)}
rows=[];summary={}
for number,(page,x0,x1,z0,z1,y0,y1,t0,t1) in calibrations.items():
 paths=[]
 for draw in d[page].get_drawings():
  c=draw.get('color');rect=draw['rect']
  if not c or c[0]<.8 or c[1]>.2 or c[2]>.2:continue
  if abs(rect.x0-x0)>.02 or abs(rect.x1-x1)>.02:continue
  if number==9 and not 60<rect.y0<80:continue
  if number==10 and not 430<rect.y0<450:continue
  if number==11 and not 60<rect.y0<80:continue
  paths.append(draw)
 if len(paths)!=1:raise ValueError('Ambiguous temperature path: '+str(number))
 items=paths[0]['items'][:300] if number==11 else paths[0]['items']
 pts=[tuple(items[0][1])]+[tuple(v[2]) for v in items if v[0]=='l']
 values=[{'figure':number,'z_m':z0+(x-x0)*(z1-z0)/(x1-x0),'T_K':t0+(y0-y)*(t1-t0)/(y0-y1)} for x,y in pts]
 rows.extend(values);peak=max(values,key=lambda r:r['T_K'])
 summary[str(number)]={'approximate_paper_peak_T_K':peak['T_K'],'approximate_peak_z_m':peak['z_m'],'samples':len(values)}
out.mkdir(parents=True,exist_ok=True)
with (out/'paper-2022-temperature-targets.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['figure','z_m','T_K']);w.writeheader();w.writerows(rows)
(out/'temperature-digitization-notes.json').write_text(json.dumps({'qualification':'Approximate vector drawings; not original reference tables. No curve is used as a simulation result.','calibrations':calibrations,'summary':summary},indent=2)+'\n')
print(json.dumps(summary,indent=2))
