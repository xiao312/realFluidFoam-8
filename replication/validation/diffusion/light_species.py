"""Screen dilute light-species transport; preserve each source's qualification."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean


def coefficient(gas, temperature, pressure, tracer, bath):
    composition = dict(bath)
    composition[tracer] = composition.get(tracer, 0) + 1e-10
    gas.TPX = temperature, pressure, composition
    index = gas.species_index(tracer)
    if len(bath) == 1:
        return float(gas.binary_diff_coeffs[index, gas.species_index(next(iter(bath)))]) * 1e4
    return float(gas.mix_diff_coeffs[index]) * 1e4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mechanism", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    fixture = Path(__file__).with_name("light-species-reference.json")
    refs = json.loads(fixture.read_text())
    if not args.mechanism.is_file():
        parser.error("Mechanism does not exist")
    if args.output is None:
        print(json.dumps(dict(mechanism=str(args.mechanism.resolve()),
                              references=refs, calculation="not run"), indent=2))
        return 0
    if args.output.exists():
        parser.error("Output exists; select a new report")
    import cantera as ct
    if ct.__version__ != "3.2.0":
        raise ValueError("Expected pinned Cantera 3.2.0")
    gases = {"author": ct.Solution(str(args.mechanism), transport_model="mixture-averaged"),
             "stock_gri30": ct.Solution("gri30.yaml", transport_model="mixture-averaged")}
    pressure = refs["pressure_pa"]
    hydrogen = []
    for series in refs["hydrogen"]["series"]:
        temperatures = refs["hydrogen"]["temperature_C"]
        if len(series["repeats"]) != len(temperatures):
            raise ValueError("Every temperature must retain its measured repeats")
        for temperature_C, repeats in zip(temperatures, series["repeats"]):
            reference = mean(repeats)
            values = {name: coefficient(gas, temperature_C+273.15, pressure,
                                        series["tracer"], series["bath"])
                      for name, gas in gases.items()}
            error = 100*(values["author"]/reference-1)
            hydrogen.append(dict(series=series["id"], carrier=series["carrier"],
                                 temperature_K=temperature_C+273.15,
                                 reference_cm2_s=reference, repeats_cm2_s=repeats,
                                 uncertainty_cm2_s=reference*.02,
                                 calculated_cm2_s=values, residual_percent=error,
                                 within_estimated_band=abs(error) <= 2))
    fits = []
    for series in refs["nist_fits"]["series"]:
        tracer, bath = series["pair"]
        for temperature in refs["nist_fits"]["sample_T_K"]:
            if not series["T_range_K"][0] <= temperature <= series["T_range_K"][1]:
                continue
            reference = math.exp(series["A"]+series["B"]/temperature
                                 + series["C"]*math.log(temperature))
            values = {name: coefficient(gas, temperature, pressure, tracer, {bath: 1})
                      for name, gas in gases.items()}
            fits.append(dict(series="-".join(series["pair"]), temperature_K=temperature,
                             reference_cm2_s=reference, calculated_cm2_s=values,
                             residual_percent=100*(values["author"]/reference-1),
                             reference_kind="evaluated temperature fit",
                             uncertainty_percent_range=series["uncertainty_percent_range"]))
    oh_ref = refs["oh_air"]
    reference = oh_ref["Dp_torr_cm2_s"]/760
    oh_values = {
        name: {bath_name: coefficient(gas, oh_ref["temperature_K"], pressure, "OH", bath)
               for bath_name, bath in [("air_21_79", {"N2": .79, "O2": .21}),
                                       ("N2_limit", {"N2": 1}), ("O2_limit", {"O2": 1})]}
        for name, gas in gases.items()
    }
    oh = dict(temperature_K=oh_ref["temperature_K"], reference_cm2_s=reference,
              reported_uncertainty_cm2_s=oh_ref["reported_uncertainty_torr_cm2_s"]/760,
              calculated_cm2_s=oh_values,
              residual_percent=100*(oh_values["author"]["air_21_79"]/reference-1),
              validation_eligible=False, reason=oh_ref["qualification"])
    later = oh_ref["later_study"]
    later_value = coefficient(gases["author"], later["temperature_K"], pressure,
                              "OH", {"N2": .79, "O2": .21})
    oh_followup = dict(temperature_K=later["temperature_K"],
                       reference_cm2_s=later["Dp_torr_cm2_s"]/760,
                       reported_uncertainty_cm2_s=later["reported_uncertainty_torr_cm2_s"]/760,
                       calculated_cm2_s=later_value,
                       residual_percent=100*(later_value/(later["Dp_torr_cm2_s"]/760)-1),
                       validation_eligible=False, reason=later["method"]+" "+later["limits"])
    gas = gases["author"]
    transport = {name: dict(gas.species(name).transport.input_data)
                 for name in ["H", "H2", "O", "OH", "H2O", "CH4", "N2", "O2"]}
    summary = {}
    for series in refs["hydrogen"]["series"]:
        selected = [r for r in hydrogen if r["series"] == series["id"]]
        summary[series["id"]] = dict(
            within_estimated_band=sum(r["within_estimated_band"] for r in selected),
            count=len(selected),
            residual_percent_range=[min(r["residual_percent"] for r in selected),
                                    max(r["residual_percent"] for r in selected)])
    for series in refs["nist_fits"]["series"]:
        name = "-".join(series["pair"])
        selected = [r for r in fits if r["series"] == name]
        summary["NIST_"+name] = dict(
            count=len(selected),
            residual_percent_range=[min(r["residual_percent"] for r in selected),
                                    max(r["residual_percent"] for r in selected)])
    stock_difference = max(abs(r["calculated_cm2_s"]["author"]
                               / r["calculated_cm2_s"]["stock_gri30"]-1)
                           for r in hydrogen+fits)
    report = dict(cantera_version=ct.__version__,
                  mechanism_sha256=hashlib.sha256(args.mechanism.read_bytes()).hexdigest(),
                  fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  references=refs, hydrogen=hydrogen, nist_fits=fits, oh_air=oh,
                  oh_air_followup=oh_followup,
                  transport_inputs=transport, summary=summary,
                  maximum_author_stock_relative_difference=stock_difference,
                  scientific_acceptance=False, new_flame_calculation=False)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(summary=summary, oh_air=oh, oh_air_followup=oh_followup,
                          stock_relative_difference=stock_difference), indent=2))
    return int(not all(r["within_estimated_band"] for r in hydrogen))


if __name__ == "__main__":
    raise SystemExit(main())
