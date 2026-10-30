"""Export exact Cantera NASA7 species metadata for an audited OpenFOAM conversion."""
import sys
import time
from datetime import datetime, timezone
from common import failure, gas_and_streams, inputs, sha256, write_json


def phase_metadata(ct, gas, mechanism, mechanism_hash, source_commit, environment_hash):
    species = []
    for item, molecular_weight in zip(gas.species(), gas.molecular_weights):
        thermo = item.thermo
        coefficients = list(thermo.coeffs)
        if type(thermo).__name__ != "NasaPoly2" or len(coefficients) != 15:
            raise ValueError(f"{item.name}: only NASA7/NasaPoly2 export is implemented")
        species.append({"name": item.name, "molecularWeight_kg_kmol": float(molecular_weight),
                        "composition": item.composition,
                        "thermo": {"model": "NASA7", "temperatureRanges": [thermo.min_temp, coefficients[0], thermo.max_temp],
                                   "lowCoeffs": coefficients[8:15], "highCoeffs": coefficients[1:8]}})
    return {"schema": "cantera-nasa7-phase/v1", "canteraVersion": ct.__version__,
            "mechanism": str(mechanism), "mechanismSha256": mechanism_hash,
            "sourceCommit": source_commit, "environmentSha256": environment_hash,
            "phase": gas.name, "thermoModel": gas.thermo_model,
            "gasConstant_J_kmol_K": ct.gas_constant, "speciesOrder": gas.species_names,
            "species": species, "transportModelQualified": False,
            "purpose": "exact thermodynamic interface export; no flame or transport validation"}


def main():
    args, config, receipt = inputs(__doc__)
    if args.plan:
        return 0
    started = time.monotonic()
    try:
        import cantera as ct
        gas, _ = gas_and_streams(ct, args, config, receipt)
        result = phase_metadata(ct, gas, args.mechanism, args.mechanism_sha256,
                                args.source_commit, args.environment_sha256)
        write_json(args.out / "phase-metadata.json", result)
        receipt.update(status="metadata_exported", elapsed_s=time.monotonic() - started,
                       completed_at=datetime.now(timezone.utc).isoformat(),
                       artifacts={"phase-metadata.json": sha256(args.out / "phase-metadata.json")})
        write_json(args.out / "receipt.json", receipt)
        print(f"Exported {len(result['species'])} species; no physical solve performed")
        return 0
    except Exception as error:
        failure(args, receipt, error, time.monotonic() - started)
        print(f"FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
