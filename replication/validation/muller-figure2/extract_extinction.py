"""Extract Figure 3's log-chi temperature curves from the bound Muller PDF."""
import argparse
import hashlib
import json
from pathlib import Path
import pymupdf
from extract import PDF_SHA256

parser = argparse.ArgumentParser()
parser.add_argument('--pdf', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
assert hashlib.sha256(args.pdf.read_bytes()).hexdigest() == PDF_SHA256
document = pymupdf.open(args.pdf)
drawings = document[5].get_drawings()
x0,x1,y0,y1 = 221.48362731933594,403.7635803222656,220.760986328125,106.8369369506836
series = {}
for label,index in [('gri30',9),('reduced',10)]:
    drawing = drawings[index]
    assert ('[]' in drawing['dashes']) == (label == 'gri30')
    points=[]
    for item in drawing['items']:
        assert item[0] == 'l'
        for point in item[1:]:
            chi = 10**(1+5*(point.x-x0)/(x1-x0))
            temperature = 2500+1500*(y0-point.y)/(y0-y1)
            if 10 <= chi <= 1e6 and (not points or points[-1] != [chi,temperature]):
                points.append([chi,temperature])
    assert all(b[0]>a[0] for a,b in zip(points,points[1:]))
    assert 5e5 < points[-1][0] < 1e6 and 3000 < points[-1][1] < 3200
    series[label] = {'path_index':index,'points':points}
record = {'schema':'muller-figure3-reference-v1','pdf_sha256':PDF_SHA256,'page':6,
          'method':'vector paths with logarithmic x calibration; clipped to visible axes',
          'axes':{'chi_s_inverse':[10,1e6],'temperature_K':[2500,4000]},
          'conditions':{'pressure_Pa':5610000,'fuel_K':288,'oxygen_K':85},
          'series':series,'interpretation':'Last drawn point is a published branch endpoint, not an independently computed extinction bracket.'}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({label:{'points':len(s['points']),'last':s['points'][-1]} for label,s in series.items()}))
