"""Extract published detailed-chemistry square markers with retained pixel evidence."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# Pixel bounds belong to the original embedded images, not a resized screenshot.
PANELS = {
    'a': {'box': [255, 25, 1223, 737], 'yrange': [200., 2200.], 'height_m': .01, 'quantity': 'T_K'},
    'b': {'box': [261, 32, 1228, 744], 'yrange': [200., 2200.], 'height_m': .04, 'quantity': 'T_K'},
    'c': {'box': [289, 35, 1228, 747], 'yrange': [0., .04], 'height_m': .01, 'quantity': 'Y_CO'},
    'd': {'box': [301, 31, 1240, 743], 'yrange': [0., .045], 'height_m': .04, 'quantity': 'Y_CO'}
}


def components(mask):
    points = set(zip(*np.where(mask)))
    while points:
        seed = points.pop()
        todo, group = [seed], [seed]
        while todo:
            y, x = todo.pop()
            for q in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
                if q in points:
                    points.remove(q)
                    todo.append(q)
                    group.append(q)
        yield group


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--images', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--plan', action='store_true')
    a = p.parse_args()
    if a.plan:
        print(json.dumps({'panels': PANELS, 'series': 'Detailed - Verhoeven; filled squares only'}))
        return
    a.out.mkdir(parents=True, exist_ok=False)
    curves = []
    for panel, calibration in PANELS.items():
        file = a.images/f'maders-fig4{panel}-original.png'
        image = Image.open(file).convert('RGB')
        mask = image.convert('L').point(lambda v: 255 if v < 50 else 0)
        mask = np.asarray(mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))) > 0
        x0,y0,x1,y1 = calibration['box']
        low,high = calibration['yrange']
        data = []
        for group in components(mask):
            ys,xs = zip(*group)
            if not 20 <= len(group) <= 250:
                continue
            width,height = max(xs)-min(xs)+1,max(ys)-min(ys)+1
            if not (8 <= width <= 16 and 8 <= height <= 16):
                continue
            px,py = (min(xs)+max(xs))/2.,(min(ys)+max(ys))/2.
            if not (x0-6 <= px <= x1 and y0 <= py <= y1):
                continue
            # Legend occupies the top right; its square must not enter the curve.
            if px > x0 + .45*(x1-x0) and py < y0 + .24*(y1-y0):
                continue
            data.append({'r_m': float((px-x0)/(x1-x0)*.03),
                         'value': float(low+(y1-py)/(y1-y0)*(high-low)),
                         'pixel_x': float(px), 'pixel_y': float(py)})
        data.sort(key=lambda row: row['r_m'])
        if len(data) < 15 or any(data[i]['r_m'] >= data[i+1]['r_m'] for i in range(len(data)-1)):
            raise ValueError('Insufficient or ambiguous square extraction '+panel)
        qa = image.copy()
        draw = ImageDraw.Draw(qa)
        for row in data:
            px,py=row['pixel_x'],row['pixel_y']
            draw.ellipse((px-9,py-9,px+9,py+9),outline=(220,0,180),width=2)
        qa.save(a.out/f'figure4{panel}-square-qa.png')
        with (a.out/f'figure4{panel}-detailed.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(data[0]))
            writer.writeheader();writer.writerows(data)
        curves.append({'id':'maders2017-fig4'+panel+'-detailed-verhoeven', **calibration,
            'series':'Detailed - Verhoeven', 'marker':'filled square',
            'image_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
            'estimated_extraction_uncertainty':{'pixels':2,'r_m':.06/(x1-x0),'value':2*(high-low)/(y1-y0)},
            'points':data})
    report={'schema':'maders-reference-digitization/v1','curves':curves,
        'method':'Black filled square opening, component shape filtering, calibrated marker centres; no reference curve fitting.',
        'limitations':'Overlapping/cropped markers may be omitted. No digitization of hollow-circle or continuous FGM series is claimed. No extrapolation.',
        'scientific_acceptance':False}
    (a.out/'curves.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({c['id']:len(c['points']) for c in curves}))


if __name__=='__main__':
    main()
