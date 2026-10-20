"""Compare methane self-diffusion with measured high-pressure data."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from prepare import correction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = [args.inputs/"ideal.yaml", args.inputs/"species.txt",
             Path(__file__).with_name("references.json"),
             Path(__file__).with_name("dawson-reference.json"),
             Path(__file__), Path(__file__).with_name("prepare.py")]
    if not all(path.is_file() for path in paths):
        parser.error("Missing mechanism, critical data or reference fixture")
    refs = json.loads(paths[3].read_text())
    if args.output is None:
        print(json.dumps(dict(inputs=str(args.inputs.resolve()), points=len(refs["rows"]),
                              calculation="not run", qualification=refs["status"],
                              pressure_basis=refs["pressure_basis"]), indent=2))
        return 0
    if args.output.exists():
        parser.error("Output exists; select a new report path")
    import cantera as ct
    if ct.__version__ != "3.2.0":
        raise ValueError("Expected pinned Cantera 3.2.0")
    gas = ct.Solution(str(paths[0]), transport_model="mixture-averaged")
    index = gas.species_index("CH4")
    critical = next(line.split() for line in paths[1].read_text().splitlines()
                    if line.split()[0] == "CH4")
    tc, pc = map(float, critical[1:3])
    table = json.loads(paths[2].read_text())["takahashi"]["table2"]
    output = []
    for row in refs["rows"]:
        temperature = row["T_K"]
        pressure = row["p_psi"]*refs["units"]["psi_to_Pa"]
        pr, tr = pressure/pc, temperature/tc
        gas.TPX = temperature, pressure, "CH4:1"
        dilute = float(gas.binary_diff_coeffs[index, index])*1e4
        factor = correction(pr, tr, table)
        corrected = dilute*factor
        shifted_pressure = pressure+refs["pressure_basis"]["required_sensitivity_Pa"]
        shifted = dilute*pressure/shifted_pressure*correction(shifted_pressure/pc, tr, table)
        output.append(dict(
            **row, pressure_Pa=pressure, Pr=pr, Tr=tr,
            table_range=bool(.1 <= pr <= 5 and 1 <= tr <= 5),
            dilute_cm2_s=dilute, corrected_cm2_s=corrected,
            pressure_plus_atmosphere_cm2_s=shifted,
            correction_factor=factor, measured_over_dilute=row["D_cm2_s"]/dilute,
            dilute_error_percent=100*(dilute/row["D_cm2_s"]-1),
            corrected_error_percent=100*(corrected/row["D_cm2_s"]-1),
            shifted_error_percent=100*(shifted/row["D_cm2_s"]-1),
            density_product_error_percent=100*(row["rho_g_cm3"]*row["D_cm2_s"]*1e6
                                                / row["rhoD_times_1e6"]-1)))
    groups = []
    for nominal in [257, 297, 323, 354]:
        selected = [r for r in output if abs(r["T_K"]-nominal) < 1]
        anchor = min(selected, key=lambda r: r["pressure_Pa"])
        for row in selected:
            row["isotherm_K"] = nominal
            row["anchor_id"] = anchor["id"]
            row["normalized_measured_factor"] = row["measured_over_dilute"]/anchor["measured_over_dilute"]
            row["normalized_model_factor"] = row["correction_factor"]/anchor["correction_factor"]
            row["normalized_shape_error_percent"] = 100*(
                row["normalized_model_factor"]/row["normalized_measured_factor"]-1)
        in_range = [r for r in selected if r["table_range"]]
        groups.append(dict(
            nominal_K=nominal, anchor_id=anchor["id"], in_range_count=len(in_range),
            corrected_error_percent_range=[min(r["corrected_error_percent"] for r in in_range),
                                           max(r["corrected_error_percent"] for r in in_range)],
            normalized_shape_error_percent_range=[
                min(r["normalized_shape_error_percent"] for r in in_range),
                max(r["normalized_shape_error_percent"] for r in in_range)]))
    if sum(g["in_range_count"] for g in groups) != sum(r["table_range"] for r in output):
        raise ValueError("An in-range observation was omitted from the isotherm grouping")
    eligible = [r for r in output if r["table_range"]]
    summary = dict(
        in_range_count=len(eligible), out_of_range_count=len(output)-len(eligible),
        dilute_mean_absolute_error_percent=mean(abs(r["dilute_error_percent"]) for r in eligible),
        corrected_mean_absolute_error_percent=mean(abs(r["corrected_error_percent"]) for r in eligible),
        corrected_max_absolute_error_percent=max(abs(r["corrected_error_percent"]) for r in eligible),
        pressure_basis_max_prediction_change_percent=max(
            abs(100*(r["pressure_plus_atmosphere_cm2_s"]/r["corrected_cm2_s"]-1))
            for r in eligible),
        density_product_max_error_percent=max(abs(r["density_product_error_percent"]) for r in output))
    report = dict(cantera_version=ct.__version__,
                  hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  critical_temperature_K=tc, critical_pressure_Pa=pc,
                  references=refs, rows=output, isotherms=groups, summary=summary,
                  normalized_shape_definition=(
                      "At each near-isotherm, divide measured D/Ddilute and F by their "
                      "values at the lowest measured pressure. This cancels a constant "
                      "dilute-scale bias and shared gradient calibration. Small temperature "
                      "differences use the fixed dilute model; anchors are not zero pressure."),
                  scientific_acceptance=False,
                  limits="Conditional self-diffusion comparison; not validation of binary pairs or flames.")
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(summary=summary, isotherms=groups), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
