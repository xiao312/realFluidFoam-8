"""Read stable counterflow checkpoints and stream a hashed tar.gz; no remote writes."""
import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile

root = Path(sys.argv[1]).resolve(strict=True)
manifest = {'observed_at': datetime.datetime.now().astimezone().isoformat(), 'cases': {}}
paths = []
for argument in sys.argv[2:]:
    key, job = argument.split(':')
    assert re.fullmatch(r'[a-z]+-[0-9]+', key) and job.isdigit()
    directory = root/'jobs'/job
    case = directory/'case'
    common = None
    for rank in range(8):
        proc = case/('processor'+str(rank))
        times = {p.name for p in proc.iterdir() if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+', p.name)}
        common = times if common is None else common & times
    times = sorted((v for v in common if float(v)>0), key=float)
    receipt = directory/'result.txt'
    finished = receipt.exists() and receipt.read_text().startswith('PASS:')
    stable = times if finished else times[:-1]
    assert stable, 'No stable nonzero checkpoint for '+job
    selected = stable[-2:]
    manifest['cases'][key] = {'job': job, 'times': selected, 'finished': finished,
        'case': 'jobs/'+job+'/case', 'inputs': (directory/'validation-inputs.txt').read_text(), 'sha256': {}}
    chosen = [p for p in (case/'constant/polyMesh').iterdir() if p.is_file()]
    chosen += [case/'system/blockMeshDict', case/'system/controlDict']
    names = ['T','p','rho','Cp','mu','kappa','U','CH4','O2','CO2','H2O','OH']
    for rank in range(8):
        proc = case/('processor'+str(rank))
        chosen.append(proc/'constant/polyMesh/cellProcAddressing')
        chosen.extend(proc/t/name for t in selected for name in names)
    for path in chosen:
        assert path.resolve().is_relative_to(root) if hasattr(path, 'is_relative_to') else str(path.resolve()).startswith(str(root)+'/')
        assert path.is_file(), str(path)
        raw = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        manifest['cases'][key]['sha256'][relative] = hashlib.sha256(raw).hexdigest()
        paths.append((path, relative, raw))

with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:
    for path, relative, raw in paths:
        assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(raw).digest(), 'Changing checkpoint '+str(path)
        info = tarfile.TarInfo(relative); info.size = len(raw)
        archive.addfile(info, io.BytesIO(raw))
    raw = json.dumps(manifest, indent=2).encode()
    info = tarfile.TarInfo('snapshot.json'); info.size = len(raw)
    archive.addfile(info, io.BytesIO(raw))
