"""Fetch a new, immutable NIST oxygen 100-atm isobar snapshot."""
import argparse
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

PARAMS=dict(Action='Data',Wide='on',ID='C7782447',Type='IsoBar',Digits='12',
    P='100',TLow='100',THigh='1000',TInc='5',RefState='DEF',TUnit='K',
    PUnit='atm',DUnit='kg/m3',HUnit='kJ/kg',WUnit='m/s',VisUnit='Pa*s',STUnit='N/m')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply']);p.add_argument('output',type=Path)
    a=p.parse_args();url='https://webbook.nist.gov/cgi/fluid.cgi?'+urlencode(PARAMS,safe='*')
    print(url)
    if a.output.exists():raise ValueError('Use a new output directory')
    if a.action=='plan':return
    with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as response:raw=response.read()
    rows=list(csv.DictReader(io.StringIO(raw.decode()),delimiter='\t'))
    assert len(rows)==181 and float(rows[0]['Temperature (K)'])==100
    assert float(rows[-1]['Temperature (K)'])==1000
    for r in rows:
        assert abs(float(r['Pressure (atm)'])-100)<1e-6
        assert float(r['Density (kg/m3)'])>0
        assert float(r['Therm. Cond. (W/m*K)'])>0
    a.output.mkdir(parents=True)
    (a.output/'oxygen-100atm.tsv').write_bytes(raw)
    (a.output/'manifest.json').write_text(json.dumps(dict(url=url,params=PARAMS,
        retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sha256=hashlib.sha256(raw).hexdigest(),rows=len(rows),
        interpretation='Current NIST reference-model evaluation, not digitized paper data'),indent=2)+'\n')


if __name__=='__main__':main()
