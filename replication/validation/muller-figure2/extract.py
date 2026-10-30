"""Extract exact vector coordinates from the fixed, owner-provided Figure 2 PDF."""
import argparse
import hashlib
import json
from pathlib import Path
import pymupdf

PDF_SHA256 = '889bba9dc807b9197efcabbebba5a06f1dbf9d55c26582d19c88fbd10f15a8b9'
# x_min, x_max, y_at_zero, y_at_axis_max, axis_max.
AXES = {
    'T': (98.95582580566406,286.4619140625,226.6476,112.1790,4000.0),
    'rho_PRVTA': (331.6908264160156,520.19873046875,227.8681,161.3325,60.0),
    'major': (98.38723754882812,288.04095458984375,393.7328796386719,277.9500427246094,1.0),
    'minor': (331.3252868652344,520.97900390625,393.7328796386719,277.9500427246094,0.1),
}
CURVES = {
    'gri30': {'T':6,'rho_PRVTA':30,'Y_O2':43,'Y_CH4':44,'Y_H2O':45,'Y_CO2':46,'Y_CO':47,'Y_OH':63,'Y_H2':64},
    'reduced': {'T':7,'rho_PRVTA':31,'Y_O2':48,'Y_CH4':49,'Y_CO2':50,'Y_H2O':51,'Y_CO':52,'Y_OH':65,'Y_H2':66},
}

def extract(pdf):
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != PDF_SHA256:
        raise ValueError('PDF differs from the calibrated source; inspect and recalibrate before extraction.')
    doc = pymupdf.open(pdf)
    drawings = doc[4].get_drawings()
    series = {}
    for mechanism, mapping in CURVES.items():
        series[mechanism] = {}
        for quantity, index in mapping.items():
            drawing = drawings[index]
            assert len(drawing['items']) > 300
            assert ('[]' in drawing['dashes']) == (mechanism == 'gri30')
            axis = quantity if quantity in AXES else ('minor' if quantity in ['Y_OH','Y_H2'] else 'major')
            x0,x1,y0,y1,maximum = AXES[axis]
            points = []
            for item in drawing['items']:
                if item[0] != 'l':
                    raise ValueError('Unexpected vector primitive; no silent conversion.')
                for point in item[1:]:
                    pair = [(point.x-x0)/(x1-x0), (y0-point.y)/(y0-y1)*maximum]
                    if not points or pair != points[-1]:
                        points.append(pair)
            assert all(-1e-6 <= z <= 1+1e-6 for z,_ in points)
            assert all(points[i+1][0] >= points[i][0]-1e-8 for i in range(len(points)-1))
            series[mechanism][quantity] = {'path_index':index,'points':points}
    full = series['gri30']
    assert abs(full['T']['points'][0][1]-85) < 0.2
    assert abs(full['T']['points'][-1][1]-288) < 0.2
    assert abs(full['rho_PRVTA']['points'][0][1]-1177.2) < 0.3
    assert abs(full['rho_PRVTA']['points'][-1][1]-42.8) < 0.3
    assert abs(full['Y_O2']['points'][0][1]-1) < 1e-6
    assert abs(full['Y_CH4']['points'][-1][1]-1) < 1e-6
    return {'schema':'muller-figure2-reference-v1','paper':'muller2015','pdf_sha256':digest,'pdf_page':5,
            'method':'PDF vector paths; axes visually checked; no image regression or smoothing',
            'conditions':{'p_Pa':5610000,'T_fuel_K':288,'T_oxidizer_K':85,'chi_st':'approximately zero; not specified numerically'},
            'axes':AXES,'series':series,'qualification':'Reference extraction only; not scientific approval.'}

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pdf',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); result=extract(args.pdf)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'curves':sum(len(v) for v in result['series'].values()),'anchors':'passed'}))
