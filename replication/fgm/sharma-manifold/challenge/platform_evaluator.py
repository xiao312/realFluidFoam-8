"""Thin Famou adapter: run a candidate, then apply the unchanged fixed evaluator."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from evaluate import evaluate as score

HERE=Path(__file__).resolve().parent


def evaluate(program_path):
    root=HERE/'runs';root.mkdir(exist_ok=True)
    run=Path(tempfile.mkdtemp(prefix='candidate-',dir=root));started=time.monotonic()
    try:
        manifest=json.loads((HERE/'manifest.json').read_text())
        for name,digest in manifest['files'].items():
            if name in ['evaluate.py','runtime.json'] or name.startswith(('references/','inputs/','physics/')):
                if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=digest:
                    raise ValueError('Fixed input changed: '+name)
        command=[sys.executable,str(Path(program_path).resolve()),'--config',str(HERE/'runtime.json'),'--output',str(run/'result.json')]
        with (run/'stdout.log').open('w') as stdout,(run/'stderr.log').open('w') as stderr:
            process=subprocess.run(command,cwd=HERE,stdout=stdout,stderr=stderr,timeout=900)
        if process.returncode:raise RuntimeError(f'Candidate exit {process.returncode}; see {run}')
        reference=json.loads((HERE/'references/curves.json').read_text())
        result=score(json.loads((run/'result.json').read_text()),reference)
        result.update(candidate_sha256=hashlib.sha256(Path(program_path).read_bytes()).hexdigest(),
            wall_seconds=time.monotonic()-started,artifact_directory=str(run),
            reference_sha256=hashlib.sha256((HERE/'references/curves.json').read_bytes()).hexdigest(),
            runtime_config_sha256=hashlib.sha256((HERE/'runtime.json').read_bytes()).hexdigest(),
            evaluator_sha256=hashlib.sha256((HERE/'evaluate.py').read_bytes()).hexdigest())
    except Exception as error:
        result={'validity':0,'combined_score':0,'error':str(error),'artifact_directory':str(run),
            'scientific_acceptance':False,'wall_seconds':time.monotonic()-started}
    (run/'metrics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':print(json.dumps(evaluate(sys.argv[1]),indent=2))
