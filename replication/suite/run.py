"""Plan or regenerate a local, source-linked replication review; never submit jobs."""
import argparse
import datetime
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from common import HERE, REPLICATION, Inputs, contained, digest, read_json, write_json


def prepare(root, config, output):
    if config.get("schema_version")!=1: raise ValueError("Unsupported campaign schema")
    for key in ("methane","nitrogen","counterflow","premixed"):
        cfg=config[key]
        if not all(cfg.get(k) for k in ("status","source_revision","build_job","executable")):
            raise ValueError(f"Missing status or run identity: {key}")
        if len(cfg["source_revision"])!=40: raise ValueError(f"Use a full source SHA: {key}")
    if config.get("dpi")!=360: raise ValueError("Qualified paper rendering uses 360 dpi")
    output=contained(root,output)
    if output.exists(): raise ValueError("Use a new output directory; previous evidence is immutable")
    if output.is_relative_to(REPLICATION.parent): raise ValueError("Generated output must stay outside the Git checkout")
    styles=read_json(HERE/"styles.json")["figures"]
    paths={}
    for year,entry in config["papers"].items():
        path=Path(entry["path"])
        if not path.is_absolute(): path=root/path
        path=path.resolve(strict=True);sha=digest(path)
        if any(s["source_sha256"]!=sha for k,s in styles.items() if k.startswith(year)):
            raise ValueError(f"Unqualified PDF: {year}; recalibrate styles for a different edition")
        paths[year]=path
    inputs=Inputs(root)
    for key in ("methane","nitrogen","counterflow","premixed"):
        if config[key]["build_job"] not in config["builds"]:
            raise ValueError(f"Missing compiled-library build identity: {key}")
    for build in config["builds"].values():
        archive=inputs.file(build["evidence_archive"])
        if digest(archive)!=build["evidence_sha256"]:
            raise ValueError("Build evidence archive hash mismatch")
    for gas in ("methane","nitrogen"):
        cfg=config[gas]
        for path in cfg["files"].values(): inputs.file(path)
        receipt=inputs.file(cfg["receipt"]).read_text(encoding="utf-8")
        if "source="+cfg["source_revision"] not in receipt or "build_job="+cfg["build_job"] not in receipt:
            raise ValueError(f"Manifest run identity conflicts with receipt: {gas}")
    contained(root,config["methane"]["reference_dir"],True)
    inputs.file(config["nitrogen"]["reference"])
    inputs.file(config["nitrogen"]["reference_manifest"])
    manifest=read_json(inputs.file(config["counterflow"]["manifest"]))
    for value in manifest["cases"].values():
        case=contained(root,value["path"],True)
        for rank in range(value["ranks"]):
            contained(root,case/f"processor{rank}"/value["time"],True)
    inputs.file(config["counterflow"]["snapshot_receipt"])
    inputs.file(config["premixed"]["snapshot"])
    catalog=read_json(HERE/"catalog.json")
    for family in catalog["families"]:
        for name in ("guide","entrypoint"):
            if not (REPLICATION/family[name]).is_file(): raise ValueError(f"Missing catalog {name}: {family['id']}")
    return output,paths,styles,inputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["plan","render"])
    parser.add_argument("project",type=Path)
    parser.add_argument("campaign",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    root=args.project.resolve(strict=True);config=read_json(args.campaign)
    output,paths,styles,inputs=prepare(root,config,args.output)
    print(f"{args.action}: {config['name']}; 27 references, 7 computed comparisons -> {output}",flush=True)
    if args.action=="plan":
        print("Read-only plan passed. No simulations submitted. New local outputs only.")
        return
    for directory in ("data","originals","captions","layers","overlays","standalone"):
        (output/directory).mkdir(parents=True,exist_ok=False)
    os.environ["MPLCONFIGDIR"]=str(contained(root,Path("cache/matplotlib")))
    import pymupdf
    from datasets import properties,counterflows,premixed
    from render import source_crops,render_all
    from paper_metrics import compare
    from report import build
    inventory=read_json(REPLICATION/"validation/figures/inventory.json")
    papers={year:pymupdf.open(path) for year,path in paths.items()}
    inventory=source_crops(papers,inventory,output,config["dpi"])
    print("Cropped all 27 original figures and captions.",flush=True)
    for script,arguments in [
        ("paper_curves.py",[paths["2022"],output/"data"]),
        ("counterflow_paper_curves.py",[paths["2022"],output/"data/paper-counterflow-curves.json"])]:
        subprocess.run([sys.executable,"-B",str(REPLICATION/"validation/figures"/script),*map(str,arguments)],check=True)
    layers,metrics=properties(config,inputs,output)
    print("Checked both methane/nitrogen EOS sweeps and NIST references.",flush=True)
    cf,contours,metrics["counterflow"]=counterflows(config,inputs,output);layers+=cf
    pm,metrics["premixed"]=premixed(config,inputs,output);layers+=pm
    metrics["paper_curve_errors"]=compare(layers,output)
    metrics["scientific_acceptance"]=False
    write_json(output/"data/metrics.json",metrics)
    write_json(output/"data/series.json",layers)
    print("Extracted counterflow profiles and premixed speed diagnostics.",flush=True)
    rendering=render_all(inventory,styles,layers,contours,output,config["dpi"])
    if config["premixed"].get("group_by_method"):
        from premixed_diagnostics import render as render_premixed_diagnostics
        render_premixed_diagnostics(config,inputs,output)
    build(inventory,config,metrics,output)
    inputs.verify()
    checkout=REPLICATION.parent
    def git(*args): return subprocess.check_output(["git","-C",str(checkout),*args],text=True).strip()
    code={str(p.relative_to(checkout)):digest(p) for p in sorted(REPLICATION.rglob("*"))
          if p.is_file() and p.suffix in (".py",".json",".txt") and "__pycache__" not in p.parts}
    products={}
    for job,build_record in config["builds"].items():
        with tarfile.open(inputs.file(build_record["evidence_archive"])) as archive:
            # Read the named member without extracting or trusting archive paths.
            receipt=archive.extractfile(f"jobs/{job}/products.sha256").read().decode("utf-8")
        products[job]={Path(line.split(None,1)[1]).name:line.split()[0] for line in receipt.splitlines() if line.strip()}
    provenance={"created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"campaign":config,
                "analysis_revision":git("rev-parse","HEAD"),"analysis_dirty":bool(git("status","--porcelain")),
                "analysis_file_hashes":code,"environment_lock":read_json(REPLICATION/"environment/lock.json"),
                "compiled_product_hashes_from_build_receipts":products,
                "source_pdf_hashes":{y:digest(p) for y,p in paths.items()},"input_hashes":inputs.hashes,
                "rendered_figures":list(rendering),"figure_count":len(inventory),
                "analysis_status":"completed; scientific acceptance is separate and false"}
    write_json(output/"provenance.json",provenance)
    write_json(output/"inventory.json",inventory)
    print("Completed local analysis and review. Numerical failure counts remain in data/metrics.json.")


if __name__=="__main__": main()
