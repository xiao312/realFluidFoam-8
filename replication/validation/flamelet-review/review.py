#!/usr/bin/env python3
"""Build a local, source-backed review without approving or rerunning science."""
from pathlib import Path
import argparse
import html
import json
import os
import shutil
import sys
from datetime import datetime, timezone


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["run", "table", "references", "out"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("sharma-figure2.json"))
    parser.add_argument("--apply", action="store_true", help="Render into a new output directory")
    return parser.parse_args()


def write_html(out, summary, config):
    escape = html.escape
    def image(name, label):
        return f'<a href="{name}.png"><img src="{name}.png" alt="{escape(label)}" loading="lazy"></a>'
    def pair(title, left, right, description):
        return f'<section><h2>{escape(title)}</h2><p>{escape(description)}</p><div class="pair">' + image(left, title) + image(right, title) + '</div></section>'
    metrics = summary["metrics"]
    lookup = summary["heldout"]
    case, models, control = summary["case"], summary["models"], summary["steady_control"]
    pressure_mpa = case["pressure_pa"] / 1e6
    fuel_t, oxidizer_t = case["fuel"]["temperature_k"], case["oxidizer"]["temperature_k"]
    steady_note = ("The independent steady control returned; its scientific acceptance remains separate."
                   if control.get("solver_returned") else
                   "The independent steady control failed and was not reused for this transient: " + str(control.get("error_type", "failure")))
    upper = models["mechanism_temperature_range_k"][1]
    range_note = (f"The initial peak exceeds the recorded {upper:g} K mechanism upper validity bound; that extrapolation is unqualified."
                  if metrics["temperature_start_K"] > upper else "The initial peak is within the recorded upper temperature bound.")
    chi = summary["integration"]["chi_st_s_inverse"]
    body = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flamelet diagnostic review</title><style>
body{{margin:0;background:#f5f4ef;color:#202923;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1200px;margin:auto;padding:35px 24px 80px}}
h1{{font-size:2.1rem;line-height:1.15}}h2{{font-size:1.45rem;margin-top:0}}section{{margin:28px 0;padding:24px;background:white;border:1px solid #dedfd7;border-radius:9px}}
.pair{{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start}}img{{display:block;width:100%;height:auto}}a{{color:#006c82}}
.warning{{border-left:6px solid #b64d32;background:#fff0e6;padding:18px 22px}}.tag{{color:#8c361b;font-weight:700}}code{{overflow-wrap:anywhere}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;border-bottom:1px solid #ddd;padding:8px}}
@media(max-width:740px){{.pair{{grid-template-columns:1fr}}main{{padding:20px 12px}}section{{padding:15px}}}}
</style><main><p class="tag">DIAGNOSTIC DATA - NOT SCIENTIFICALLY ACCEPTED</p>
<h1>Physical flamelet, table and paper comparison</h1>
<p>Actual retained integration: {metrics['states']} states, {metrics['final_time_s'] * 1e3:g} ms.
{escape(summary['mechanism_name'])}, {escape(models['thermo'])}, {pressure_mpa:g} MPa; CH4 at {fuel_t:g} K, O2 at {oxidizer_t:g} K;
{escape(models['transport'])}; chi_st = {chi:g} s<sup>-1</sup>. The trajectory starts from fresh HP equilibrium.</p>
<div class="warning"><strong>Energy discrepancy: {metrics['maximum_enthalpy_error_J_kg']/1000:.2f} kJ/kg.</strong>
The producer reports this maximum deviation from linear inlet enthalpy. These plots retain the original values and cannot establish whether an energy-implementation correction is sufficient.
{escape(steady_note)}. {escape(range_note)}
The table's coverage and source interpolation require separate qualification. A completed solver process is not physical qualification.</div>
<section><h2>Measured checks</h2><table><tr><th>Measurement</th><th>Retained value</th></tr>
<tr><td>Peak temperature, initial / final</td><td>{metrics['temperature_start_K']:.2f} / {metrics['temperature_end_K']:.2f} K</td></tr>
<tr><td>Raw C at stoichiometry, initial / final</td><td>{metrics['progress_start']:.6g} / {metrics['progress_end']:.6g}</td></tr>
<tr><td>Maximum element mass-fraction error</td><td>{metrics['maximum_element_error']:.4g}</td></tr>
<tr><td>Maximum regularized Griffon/Cantera species-rate discrepancy</td><td>{metrics['maximum_kinetics_rate_error']:.4g}; denominator |Cantera rate| + 1 kg/(m3 s)</td></tr>
<tr><td>Whole held-out profiles / evaluated states / out-of-coverage states</td><td>{lookup['profiles']} / {lookup['evaluated']} / {lookup['out_of_coverage']}</td></tr></table></section>
'''
    body += pair("Physical time and energy", "time-evolution", "energy-and-kinetics",
                 "Time uses a symmetric logarithmic axis so the rapid extinction and the full 1 ms duration remain visible. Zero time is retained.")
    body += pair("Profiles and held-out interpolation", "temperature-profiles", "heldout-errors",
                 "These are actual physical-time profiles. Whole-profile held-out errors test interpolation separately from kinetics and preserve failed source behavior.")
    body += f'''<section id="sharma-context"><h2>Sharma Figure 2: scope of comparison</h2>
<p>The paper uses the Kong mechanism at 6 MPa. Our current trajectory uses {escape(summary['mechanism_name'])} at {pressure_mpa:g} MPa,
with fuel/oxidizer at {fuel_t:g}/{oxidizer_t:g} K.
Equation 22 defines c = (Y_CO2 + Y_CO)/(Y_CO2 + Y_CO)_eq for these pure reactant streams.
We use that formula with our own initial HP-equilibrium denominator at each Z. All time-ordered folds and multiple values are retained.
There is no fitted curve or numerical paper agreement score. The paper reports f_st = 0.2132; pure CH4/O2 elemental stoichiometry gives approximately 0.20044.
The origin of this reported difference remains unresolved; it is not evidence by itself for a different mixture-fraction definition.</p>
<p>The local table coordinate eta only spans measured progress coverage and is shown separately. It must not be presented as the paper's normalized c.</p></section>'''
    for panel in config["panels"]:
        pid = panel["id"]
        body += pair(f"Sharma Figure 2: {panel['ylabel']}", f"trajectory-{pid}", f"original-{pid}",
                     "Left: actual trajectory using our initial-equilibrium normalization. Right: original paper crop. Models and conditions differ; this is not an accepted reproduction.")
        body += pair(f"Visible paper data and table coordinate: {panel['ylabel']}", f"table-{pid}", f"paper-digitized-{pid}",
                     "Left: our local table eta coordinate. Right: paper c extracted from visible colored pixels. Missing columns remain gaps; these axes are not interchangeable.")
        body += f'<p><a href="digitization-{pid}-overlay.png">Inspect extraction overlay</a> | <a href="digitized-{pid}.csv">Extracted CSV</a></p>'
    body += f'''<section id="citation"><h2>Reference and provenance</h2><p>{escape(config['caption'])}</p>
<p><a href="{escape(config['url'])}">{escape(config['paper'])}</a>. Local PDF SHA256: <code>{config['pdf_sha256']}</code>.</p>
<p>Scientific source: <code>{escape(summary['scientific_source'])}</code>. Upstream Spitfire: <code>{escape(summary['upstream_revision'])}</code>.</p>
<p><a href="review.json">Input, code and output hashes; metrics and limitations</a> | <a href="trajectory-progress-series.json">Plotted time-ordered progress data</a></p>
<p>Paper crops, results and review artifacts are local inputs/outputs. This review performs no publication, merge or scientific acceptance.</p></section></main></html>'''
    (out / "index.html").write_text(body, encoding="utf-8")


def main():
    args = arguments()
    from inputs import digest, load_inputs, read_json, whole_profile_summary
    data = load_inputs(args.run, args.table)
    config = read_json(args.config)
    if config["schema"] != "paper-color-calibration/v1":
        raise ValueError("Unsupported calibration schema")
    references = {p["filename"]: digest(args.references / p["filename"]) for p in config["panels"]}
    plan = {"run": str(args.run.resolve()), "table": str(args.table.resolve()),
            "output": str(args.out.resolve()), "inputs": data["input_hashes"],
            "reference_hashes": references, "calibration_sha256": digest(args.config), "apply": args.apply}
    if not args.apply:
        print(json.dumps(plan, indent=2)); return
    args.out.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault("MPLCONFIGDIR", str((args.out / "matplotlib-cache").resolve()))
    os.environ["MPLBACKEND"] = "Agg"
    import numpy as np
    from digitize import extract_panel, write_extraction
    from plots import configure_style, time_diagnostics, temperature_profiles, progress_comparisons, lookup_errors
    configure_style()
    extractions = {}
    for panel in config["panels"]:
        source = args.references / panel["filename"]
        extracted = extract_panel(source, panel, config)
        extractions[panel["id"]] = extracted
        write_extraction(extracted, source, args.out)
        shutil.copyfile(source, args.out / f"original-{panel['id']}.png")
    time_diagnostics(data, args.out)
    temperature_profiles(data, args.out)
    series = progress_comparisons(data, extractions, config, args.out)
    lookup_errors(data, args.out)
    (args.out / "trajectory-progress-series.json").write_text(json.dumps(series) + "\n")
    d, a = data["diagnostics"], data["trajectory"]
    summary = {"schema": "flamelet-review/v1", "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_plan": plan, "scientific_source": data["receipt"]["source_commit"],
        "upstream_revision": data["receipt"]["models"]["upstream_revision"],
        "producer_environment_identity": data["receipt"]["environment_sha256"],
        "case": data["receipt"]["case"], "models": data["receipt"]["models"],
        "integration": data["receipt"]["integration"], "steady_control": data["receipt"]["steady_control"],
        "mechanism_name": Path(data["receipt"]["mechanism_path"]).name,
        "metrics": {"states": len(a["time_s"]), "final_time_s": float(a["time_s"][-1]),
                    "temperature_start_K": float(a["T_K"][0].max()), "temperature_end_K": float(a["T_K"][-1].max()),
                    "progress_start": d["progress_st_start_end"][0], "progress_end": d["progress_st_start_end"][1],
                    **{k: d[k] for k in ["maximum_enthalpy_error_J_kg", "maximum_element_error", "maximum_kinetics_rate_error"]}},
        "heldout": whole_profile_summary(data["heldout"]),
        "digitization": {k: {c["name"]: len(c["points"]) for c in v["curves"]} for k, v in extractions.items()},
        "coordinate_policy": "Trajectory C/Ceq(initial HP), same paper formula with different mechanism/conditions; table eta is separate; retain folds",
        "paper_rms": None, "scientific_acceptance": False,
        "code_hashes": {p.name: digest(p) for p in sorted(Path(__file__).parent.glob("*.py"))}}
    write_html(args.out, summary, config)
    summary["artifact_hashes"] = {p.name: digest(p) for p in sorted(args.out.iterdir()) if p.is_file()}
    (args.out / "review.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"output": str(args.out), "metrics": summary["metrics"], "digitization": summary["digitization"]}, indent=2))


if __name__ == "__main__":
    main()
