"""Exercise rejection of accidental restarts without running CFD."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from prepare import verify

root=Path(sys.argv[1]).resolve()
root.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=root) as temporary:
    case=Path(temporary)
    (case/'system').mkdir();(case/'constant').mkdir()
    for directory in [case]+[case/('processor'+str(i)) for i in range(8)]:
        (directory/'0').mkdir(parents=True)
        for name in ('T','p','U','CH4','O2','N2','OH'):(directory/'0'/name).write_text('original fixture')
    (case/'fresh-start-inputs.json').write_text(json.dumps({'family':'native','initialization':'generated_original_zero'}))
    control=case/'system/controlDict'
    control.write_text('startFrom startTime; startTime 0; application solver;')
    verify('native',case)
    for text in ('startFrom latestTime; startTime 0;', 'startFrom startTime; startTime 5e-5;'):
        control.write_text(text)
        try:verify('native',case)
        except ValueError:pass
        else:raise AssertionError('Restart policy not enforced')
    control.write_text('startFrom startTime; startTime 0;')
    (case/'processor0/0.00005').mkdir()
    try:verify('native',case)
    except ValueError:pass
    else:raise AssertionError('Positive saved time not rejected')
    path=Path(__file__).resolve().parent.parent/'flame-tracking/prepare.py'
    spec=importlib.util.spec_from_file_location('checkpoint_prepare',path)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    try:old.prepare('plan',case,'phi110','full',root)
    except ValueError as error:assert 'explicit owner authorization' in str(error)
    else:raise AssertionError('Legacy checkpoint launcher not blocked')
print('PASS: original-zero accepted; latestTime, nonzero start, saved states and unauthorized continuation rejected')
