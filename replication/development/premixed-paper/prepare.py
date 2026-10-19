"""Prepare a declared reconstruction of the paper's central-ignition case."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

MODULE=Path(__file__).resolve().parent
FLAMES=MODULE.parents[1]/"validation/flames"


def temperature(x, length, width, peak):
    distance=abs(x-length/2)
    return 298. if distance>=width/2 else 298.+(peak-298.)*.5*(1+math.cos(2*math.pi*distance/width))


def configuration(key,mode):
    cfg=json.loads((MODULE/"cases.json").read_text())[key]
    if mode not in ("smoke","full"): raise ValueError("Expected smoke/full")
    if abs(cfg["length_m"]/cfg["cells"]-5e-7)>1e-15: raise ValueError("Paper mesh is 0.5 um")
    return dict(cfg,key=key,mode=mode,ranks=8,pressure_Pa=10132500,unburned_temperature_K=298,
        end_time_s=1e-9 if mode=="smoke" else 2e-4,initial_delta_t_s=1e-10,max_co=.1,
        write_interval_s=1e-9 if mode=="smoke" else 1e-5,
        diagnostic_interval_steps=1 if mode=="smoke" else 10,
        maximum_allocated_core_hours=8 if mode=="smoke" else 192,
        status="paper-method reconstruction; numerical and ignition/domain independence unqualified")


def prepare(action,key,output,mode):
    cfg=configuration(key,mode)
    print(json.dumps(dict(configuration=cfg,output=str(output.resolve())),indent=2))
    if output.exists(): raise ValueError("Refusing existing case")
    if action=="plan": return
    subprocess.run([sys.executable,"-B",str(FLAMES/"generate_premixed.py"),
        str(FLAMES.parent/"inputs"),str(output),str(cfg["phi"])],check=True)
    def write(name,text): (output/name).write_text(text,encoding="utf8")
    mesh=(output/"system/blockMeshDict").read_text().replace("convertToMeters 0.001","convertToMeters 1")
    mesh=mesh.replace("(2 ","("+str(cfg["length_m"])+" ").replace("0.01","0.00001")
    mesh=mesh.replace("(200 1 1)","("+str(cfg["cells"])+" 1 1)")
    write("system/blockMeshDict",mesh)
    write("0/p",(output/"0/p").read_text().replace("lInf 0.002","lInf "+str(cfg["length_m"])))
    values=[temperature((i+.5)*cfg["length_m"]/cfg["cells"],cfg["length_m"],cfg["kernel_width_m"],cfg["kernel_temperature_K"]) for i in range(cfg["cells"])]
    field="internalField nonuniform List<scalar>\n"+str(len(values))+"\n(\n"+"\n".join(format(v,".16g") for v in values)+"\n);"
    write("0/T",re.sub(r"internalField\s+uniform\s+[^;]+;",field,(output/"0/T").read_text()))
    # Ignition exists entirely in 0/T. A stale setFields file must not reset it.
    (output/"system/setFieldsDict").unlink()
    from_header='FoamFile { version 2.0; format ascii; class dictionary; object '
    write("system/controlDict",from_header+"controlDict; }\n"+f"""
application rfPaperReactingFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {cfg['end_time_s']};
deltaT {cfg['initial_delta_t_s']}; adjustTimeStep {'no' if mode=='smoke' else 'yes'};
maxCo {cfg['max_co']}; maxDeltaT {cfg['max_delta_t_s']};
writeControl runTime; writeInterval {cfg['write_interval_s']};
writeFormat ascii; writePrecision 12; timePrecision 12; purgeWrite 0;
runTimeModifiable true;
""")
    write("system/decomposeParDict",from_header+"decomposeParDict; }\nnumberOfSubdomains 8;\nmethod simple;\nsimpleCoeffs { n (8 1 1); delta 0.001; }\n")
    write("constant/flameSpeedProperties",from_header+"flameSpeedProperties; }\n"+
        f"enabled true; interval {cfg['diagnostic_interval_steps']}; levels (1e-5 2e-5 3e-5); initialFreshDensity -1;\n")
    pilot=json.loads((output/"pilot.json").read_text())
    pilot.update(length_m=cfg["length_m"],cells=cfg["cells"],spacing_m=5e-7,
        kernel_width_m=cfg["kernel_width_m"],kernel_temperature_K=cfg["kernel_temperature_K"],
        kernel_shape="compact cosine",initial_velocity_m_s=0.)
    write("pilot.json",json.dumps(pilot,indent=2)+"\n")
    write("paper-case.json",json.dumps(cfg,indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=["plan","apply"]);p.add_argument("key");p.add_argument("output",type=Path);p.add_argument("mode",choices=["smoke","full"])
    a=p.parse_args();prepare(a.action,a.key,a.output,a.mode)
