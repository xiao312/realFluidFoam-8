"""Plan/apply an observer-only live controlDict edit after scheduled qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def block(library,interval=10):
    return '''
functions
{
    heatReleaseUsed
    {
        type rfHeatReleaseMonitor;
        libs ("%s");
        crossSectionArea 1e-10;
        executeControl timeStep;
        executeInterval %d;
        writeControl writeTime;
    }
}
''' % (library,interval)


def attach(action,case,qualification):
    case=case.resolve();qualification=qualification.resolve()
    root=qualification.parent.parent
    if root.name!='realfluidfoam' or qualification.parent.name!='jobs':
        raise ValueError('Expected project jobs/QUALIFICATION_ID')
    if case.parent.parent!=root/'jobs' or case.name!='case':
        raise ValueError('Expected a project jobs/JOB_ID/case path')
    if (qualification/'result.txt').read_text().strip()!='PASS: heat-release monitor qualification':
        raise ValueError('Monitor qualification has not passed')
    lib=qualification/'monitor-lib/librfHeatReleaseMonitor.so'
    expected=(qualification/'monitor-library.sha256').read_text().split()[0]
    if hashlib.sha256(lib.read_bytes()).hexdigest()!=expected:raise ValueError('Library hash mismatch')
    path=case/'system/controlDict';original=path.read_bytes();text=original.decode()
    if not re.search(r'runTimeModifiable\s+true\s*;',text):raise ValueError('Runtime reread disabled')
    if re.search(r'\bfunctions\s*\{|#include',text):raise ValueError('Existing functions/include need explicit review')
    library='/work/'+str(lib.relative_to(root)).replace('\\','/')
    proposed=(text+block(library)).encode()
    receipt={'case':str(case),'qualification_job':qualification.name,'library_sha256':expected,
        'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(proposed).hexdigest(),
        'change':'append heatReleaseUsed observer; numerical settings unchanged',
        'source_stage':'integrated chemistry rates retained from species/energy solve',
        'history':'starts at runtime attachment, no backfill'}
    print(json.dumps(receipt,indent=2))
    if action=='plan':return
    evidence=case.parent/'heat-release-attachment'
    evidence.mkdir(exist_ok=False)
    (evidence/'controlDict.before').write_bytes(original)
    (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if path.read_bytes()!=original:raise ValueError('controlDict changed during preparation')
    temp=path.with_name('controlDict.heat-release.tmp');temp.write_bytes(proposed);temp.replace(path)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply']);p.add_argument('case',type=Path);p.add_argument('qualification',type=Path)
    a=p.parse_args();attach(a.action,a.case,a.qualification)
