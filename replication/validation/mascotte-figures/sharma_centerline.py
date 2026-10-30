"""Digitize Sharma Figure 4b without interpreting the flame-location band as T."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import pymupdf

PDF_SHA = '65ae91e8734d8006f4274c70f548f969ab18ca698d8aad8d3b3384882356349c'
AXIS = {'x_zero_pixel':80.6, 'x_0_2_m_pixel':468.0,
        'T_zero_pixel':355.8, 'T_3500_K_pixel':30.8}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.pdf.read_bytes()).hexdigest() != PDF_SHA:
        raise ValueError('Unexpected paper PDF; inspect and recalibrate.')
    document = pymupdf.open(args.pdf)
    images = [entry for entry in document[9].get_images(full=True) if entry[0] == 79]
    assert len(images) == 1 and images[0][2:4] == (472,405)
    raw = document.extract_image(79)['image']
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    rgb = np.asarray(im).astype(float)
    red = (rgb[:,:,0]>150)&(rgb[:,:,1]<140)&(rgb[:,:,2]<140)
    blue = (rgb[:,:,2]>150)&(rgb[:,:,0]<150)&(rgb[:,:,1]<150)
    overlay = im.copy(); draw = ImageDraw.Draw(overlay)
    series = {}
    for name, mask, color in [('fine',red,'black'),('finer',blue,'green')]:
        points = []
        for x in range(82,468):
            # Actual curves are below row 160; rows 77 and 105 contain legends.
            yy = np.flatnonzero(mask[160:355,x])+160
            if not len(yy):
                continue
            y = float(np.median(yy))
            position = (x-AXIS['x_zero_pixel'])/(AXIS['x_0_2_m_pixel']-AXIS['x_zero_pixel'])*0.2
            temperature = (AXIS['T_zero_pixel']-y)/(AXIS['T_zero_pixel']-AXIS['T_3500_K_pixel'])*3500
            points.append([position,temperature])
            if x%5 == 0:draw.ellipse((x-1,y-1,x+1,y+1),fill=color)
        assert len(points)>150
        peak = max(points,key=lambda pair:pair[1])
        assert 1700<peak[1]<2050 and .045<peak[0]<.065
        series[name] = {'points':points, 'peak':peak,
                        'method':'column median colored pixels; dashed gaps retained'}
    record = {'schema':'sharma-centerline-reference-v1','paper':'sharma2023',
        'target':'sharma2023-fig-4b','pdf_sha256':PDF_SHA,'page':10,'image_xref':79,
        'image_sha256':hashlib.sha256(raw).hexdigest(),'axes':AXIS,'series':series,
        'reading_uncertainty':{'x_one_pixel_m':0.2/387.4,'T_one_pixel_K':3500/325,
                               'note':'Line thickness and calibration add uncertainty; no statistical confidence interval.'},
        'observable':'time-averaged centerline temperature',
        'experimental_band':'flame location only; not temperature observations',
        'scientific_acceptance':'not_assigned'}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    overlay.save(args.out.with_suffix('.overlay.png'))
    print(json.dumps({'output':str(args.out),'curves':{k:{'points':len(v['points']),'peak':v['peak']} for k,v in series.items()}}))


if __name__ == '__main__':main()
