"""Compare actual adapter samples with independent correlation requests."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from prepare import correction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requests", type=Path)
    parser.add_argument("samples", type=Path)
    args = parser.parse_args()
    with args.requests.open() as stream:
        expected = list(csv.DictReader(stream))
    with args.samples.open() as stream:
        actual = list(csv.DictReader(stream))
    if not expected or len(expected) != len(actual):
        raise ValueError("Missing or extra property samples")
    failures, errors, mixture, symmetry = [], [], [], []
    table = json.loads(Path(__file__).with_name("references.json").read_text())["takahashi"]["table2"]
    for index, (request, sample) in enumerate(zip(expected, actual)):
        if int(sample["row"]) != index:
            raise ValueError("Sample order differs")
        factor = float(sample["factor"])
        pr, tr = float(sample["actual_Pr"]), float(sample["actual_Tr"])
        if max(abs(pr/float(request["Pr"])-1), abs(tr/float(request["Tr"])-1)) > 1e-12:
            raise ValueError("Actual thermodynamic state differs from request")
        # Evaluate at the actual state: roundoff across Pr=0.1 can select the
        # adapter's discontinuous unity policy. Do not disguise this as table error.
        error = abs(factor/correction(pr, tr, table)-1)
        mix = float(sample["max_mix_relative_error"])
        sym = float(sample["symmetry_relative_error"])
        if not all(math.isfinite(value) for value in (factor, error, mix, sym)):
            raise ValueError("Nonfinite probe result")
        if error > 1e-10 or mix > 1e-7 or sym > 1e-12:
            failures.append(dict(row=index, request=request, relative_error=error,
                                 mixture_error=mix, symmetry_error=sym))
        errors.append(error); mixture.append(mix); symmetry.append(sym)
    # Trace species complement subtraction loses precision near a pure bath;
    # mixture tolerance here is 1e-7. Ordinary flame-state gate remains 1e-10.
    report = dict(samples=len(actual), failures=failures,
                  maximum_factor_relative_error=max(errors),
                  maximum_mixture_relative_error=max(mixture),
                  maximum_symmetry_relative_error=max(symmetry),
                  input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (args.requests, args.samples)},
                  scientific_acceptance=False)
    print(json.dumps(report, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
