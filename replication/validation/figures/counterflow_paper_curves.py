"""Extract both published line series in Figures 9–11 of the supplied 2022 PDF.

Usage: python counterflow_paper_curves.py PDF OUTPUT_JSON
The fixed hash and inspected path groups prevent silent use with a different PDF.
Coordinates are approximate drawing values, not original simulation tables.
"""
import hashlib
import json
from pathlib import Path
import sys
import fitz

SHA256 = '716602f37f6b27f62791986770788e450225bc688686c54049849ecfe8414a60'
# (reference path, Nguyen path, Nguyen continuous group).
PATHS = {
    9: {'T':(566,616,0),'CH4':(277,443,0),'CO2':(318,444,0),
        'H2O':(357,445,0),'O2':(384,446,0),'OH':(411,447,0),
        'rho':(0,88,0),'Cp':(47,88,1),'mu':(754,847,0),'kappa':(797,848,0)},
    10: {'T':(1723,1774,0),'CH4':(1925,2075,0),'O2':(1963,2076,0),
         'CO2':(1985,2077,0),'H2O':(2022,2078,0),'OH':(2044,2079,0),
         'Cp':(1106,1187,0),'rho':(1143,1187,1),'kappa':(1377,1462,0),'mu':(1422,1462,1)},
    11: {'T':(297,344,0),'rho':(249,344,1),'CH4':(0,81,0),'O2':(33,81,1),'CO2':(56,81,2)},
}
# Two inspected tick positions and their physical values: y1, value1, y2, value2.
CALIBRATION = {
    9: {'T':(167.369,500,69.521,2000),'species':(181.397034,0,65.294006,1),
        'rho':(330.586,.2,214.108,.7),'Cp':(318.770,1200,214.136,2700),
        'mu':(332.712,0,221.298,6e-5),'kappa':(332.712,.03,216.237,.14)},
    10: {'T':(536.499,500,453.208,2000),'species':(545.599976,0,435.776031,1),
         'rho':(693.217,40,582.996,160),'Cp':(678.714,1500,583.192,3500),
         'mu':(697.824,0,586.379,7e-5),'kappa':(693.699,.06,578.414,.20)},
    11: {'T':(173.053,500,82.866,2000),'rho':(179.611,20,64.830,120),
         'species':(344.5410156,0,223.1350098,1)},
}


def groups(drawing):
    """Split disconnected subpaths, retaining drawing order and small x reversals."""
    result = []
    for item in drawing['items']:
        assert item[0] == 'l', 'Unexpected curve geometry'
        start, end = item[1:]
        if not result or abs(start-result[-1][-1]) > .001:
            result.append([start])
        result[-1].append(end)
    return result


def extract(pdf):
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == SHA256, 'Unqualified source PDF'
    doc = fitz.open(pdf)
    curves = []
    for figure, fields in PATHS.items():
        page = 11 if figure < 11 else 12
        drawings = doc[page].get_drawings()
        for field, (reference, nguyen, group) in fields.items():
            species = field in {'CH4','O2','CO2','H2O','OH'}
            if figure == 9:
                xmin,xmax = (326.696991,487.876007) if species or field in {'mu','kappa'} else (111.789001,272.970001)
                zmin,zmax = .003,.018
            elif figure == 10:
                xmin,xmax = (325.615997,485.066010) if species or field in {'mu','kappa'} else (113.017006,272.467010)
                zmin,zmax = .002,.0035
            else:
                xmin,xmax,zmin,zmax = 80.1669998,249.036987,.0105,.012
            calibration = CALIBRATION[figure]['species' if species else field]
            y1,v1,y2,v2 = calibration
            scale = (100 if figure==9 else 500) if field=='OH' else 1
            for series,index,part in [('benchmark',reference,0),('nguyen',nguyen,group)]:
                points = groups(drawings[index])[part]
                assert len(points)>30
                z = [zmin+(p.x-xmin)/(xmax-xmin)*(zmax-zmin) for p in points]
                values = [(v1+(p.y-y1)/(y2-y1)*(v2-v1))/scale for p in points]
                assert min(z)>=zmin-1e-5 and max(z)<=zmax+1e-5
                curves.append({'figure':figure,'field':field,'series':series,'page_index':page,
                    'drawing_index':index,'continuous_group':part,'z_m':z,'value':values,
                    'x_calibration':[xmin,zmin,xmax,zmax],'y_calibration':calibration,
                    'paper_display_scale':scale})
    assert len(curves)==50
    return {'source_sha256':SHA256,'qualification':'Approximate PDF line digitization; no extrapolation, axial alignment, or recovered author tables.',
        'benchmark_labels':{'9':'OPPDIF','10':'OPPDIF','11':'Juanos and Sirignano'},'curves':curves}


if __name__ == '__main__':
    result = extract(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
    print('Extracted 50 curves: both paper series for every published quantity in Figures 9–11.')
