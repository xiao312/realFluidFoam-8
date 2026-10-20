"""Evaluate frozen conductivity measurements without fitting or solving flames."""
import argparse
import hashlib
import json
from pathlib import Path

from conductivity_math import R, conductivity, srk_volumes


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("inputs", "reference", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    paths = [args.inputs / "ideal.yaml", args.inputs / "species.txt", args.reference]
    if not all(path.is_file() for path in paths) or args.output.exists():
        parser.error("Require existing inputs and a new output file")
    data = json.loads(args.reference.read_text(encoding="utf-8"))
    composition = data["composition"]["reported_percent"]
    basis = data["composition"]["reported_basis"]
    if basis not in (None, "mole", "mass") or not composition or not data["rows"]:
        parser.error("Expected an explicit composition/basis and measurement rows")
    bases = ("mole", "mass") if basis is None else (basis,)
    print(json.dumps(dict(output=str(args.output.resolve()),
                          states=len(bases) * len(data["rows"]), flame_solve=False,
                          composition_basis_qualified=basis is not None)))
    if args.action == "plan":
        return
    import cantera as ct
    import numpy as np

    if ct.__version__ != "3.2.0":
        raise ValueError("Expected Cantera 3.2.0")
    if not all(np.isfinite(value) and value > 0 for value in composition.values()):
        raise ValueError("Composition percentages must be finite and positive")
    if not np.isclose(sum(composition.values()), 100, rtol=0, atol=1e-8):
        raise ValueError("Reported percentages must sum to 100")
    gas = ct.Solution(str(paths[0]), transport_model="mixture-averaged")
    records = [line.split() for line in paths[1].read_text().splitlines()]
    if gas.species_names != [row[0] for row in records]:
        raise ValueError("Mechanism/species-table order differs")
    parameters = np.array([[float(v) for v in row[1:]] for row in records])
    rows = []
    for interpretation in bases:
        for point in data["rows"]:
            temperature = point["conductivity_temperature_K"]
            pressure = point["pressure_Pa"]
            measured = point["thermal_conductivity_W_per_m_K"]
            if not all(np.isfinite(v) and v > 0 for v in (temperature, pressure, measured)):
                raise ValueError("Measurement T, p and conductivity must be positive")
            if interpretation == "mole":
                gas.TPX = temperature, pressure, composition
            else:
                gas.TPY = temperature, pressure, composition
            x, cp = gas.X.copy(), gas.standard_cp_R.copy()
            volume, _ = srk_volumes(temperature, pressure, x, parameters)
            ideal = gas.thermal_conductivity
            native = conductivity(temperature, volume, x, parameters, cp)
            # The established dense-increment diagnostic subtracts EH at 1 Pa.
            dilute = conductivity(temperature, R * temperature, x, parameters, cp)
            coupled = conductivity(temperature, volume, x, parameters, cp, "coupled",
                                   "tn1039", True)
            predictions = {
                "Cantera_dilute": ideal,
                "EH_partial_native": native["lambda_W_mK"],
                "EH_dense_increment": ideal + native["lambda_W_mK"] - dilute["lambda_W_mK"],
                "EH_coupled_TN1039": coupled["lambda_W_mK"],
            }
            if not all(np.isfinite(v) and v > 0 for v in predictions.values()):
                raise ValueError("Nonpositive or nonfinite prediction")
            rows.append(dict(
                run_point=point["run_point"], basis_interpretation=interpretation,
                T_K=temperature, pressure_Pa=pressure,
                mole_fractions={name: float(x[gas.species_index(name)]) for name in composition},
                reference_W_mK=measured, evaluated_W_mK=predictions,
                signed_error_percent={key: 100 * (value / measured - 1)
                                      for key, value in predictions.items()},
                srk_molar_density_mol_L=1 / volume,
                mapping={"partial": native, "coupled": coupled}))
    summary = []
    for interpretation in bases:
        subset = [row for row in rows if row["basis_interpretation"] == interpretation]
        for name in rows[0]["evaluated_W_mK"]:
            errors = [row["signed_error_percent"][name] for row in subset]
            summary.append(dict(basis_interpretation=interpretation, model=name,
                                signed_bias_percent=float(np.mean(errors)),
                                rms_error_percent=float(np.sqrt(np.mean(np.square(errors)))),
                                maximum_absolute_error_percent=float(np.max(np.abs(errors)))))
    paths += [Path(__file__), Path(__file__).with_name("conductivity_math.py")]
    report = dict(
        rows=rows, summary=summary, cantera_version=ct.__version__,
        input_sha256={path.name: digest(path) for path in paths}, source_measurement=data,
        scientific_acceptance=False,
        limits=["Composition and complete measurement-accuracy qualification remain separate",
                "No interpretation or model is selected by its residual",
                "A property score does not validate hydrogen flame transport",
                "SRK prescribed-volume EH hybrid, not the full TRAPP reference EOS",
                "No empirical coefficient, model or flame input changed"])
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
