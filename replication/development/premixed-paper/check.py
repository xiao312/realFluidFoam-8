"""Finalize boundary density, retain input hashes, and verify isolated runs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

MODULE=Path(__file__).resolve().parent
FLAMES=MODULE.parents[1]/"validation/flames"
sys.path.insert(0,str(FLAMES/"adaptive"))
from fields import inspect,times


def finalize(case):
    subprocess.run([sys.executable,"-B",str(FLAMES/"finalize_premixed.py"),str(case)],check=True)
    rho=json.loads((case/"pilot.json").read_text())["unburned_density_kg_m3"]
    path=case/"constant/flameSpeedProperties"
    path.write_text(path.read_text().replace("initialFreshDensity -1;",f"initialFreshDensity {rho:.16g};"))
    hashes={str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest()
        for sub in ["0","constant","system"] for p in sorted((case/sub).rglob("*")) if p.is_file()}
    (case/"input-sha256.json").write_text(json.dumps(hashes,indent=2))


def check(job,mode):
    case=job/"case"; cfg=json.loads((case/"paper-case.json").read_text())
    latest=times(case,8)[-1]
    result,_=inspect(case,8,latest)
    if abs(float(latest)-cfg["end_time_s"])>1e-12: raise ValueError("Endpoint not reached")
    with (case/"processor0/flame-speed.csv").open() as stream: rows=list(csv.DictReader(stream))
    if not rows or set(r["stage"] for r in rows)!={"integrated_species_solve","instantaneous_end_step"}:
        raise ValueError("Missing both diagnostic stages")
    result.update(diagnostic_rows=len(rows),valid_rows=sum(r["status"]=="valid" for r in rows),
        status="finite normalized endpoint; flame convergence not established")
    if mode=="smoke":
        baseline=job/"diagnostics-off"; mismatches=[]; count=0
        for p in case.glob("processor*/"+latest+"/*"):
            if not p.is_file():continue
            other=baseline/p.relative_to(case)
            body=lambda path: re.sub(r"FoamFile\s*\{.*?\}","",path.read_text(),flags=re.S)
            if not other.exists() or body(p)!=body(other):mismatches.append(str(p.relative_to(case)))
            count+=1
        result.update(compared_fields=count,mismatches=mismatches)
        if mismatches: raise ValueError("Diagnostic changed fields: "+str(mismatches[:10]))
    (job/"endpoint-check.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("action",choices=["finalize","check"]);p.add_argument("path",type=Path);p.add_argument("mode",nargs="?",default="smoke")
    a=p.parse_args();finalize(a.path) if a.action=="finalize" else check(a.path,a.mode)
