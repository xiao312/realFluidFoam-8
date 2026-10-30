# Real-fluid thermodynamic input adapter

This module combines exact NASA7 data from the identified Cantera phase with
critical and dense-fluid transport parameters from Nguyen's retained GRI30
tutorial. It prepares a controlled input for the full realFluidFoam library;
it does not run or validate that library.

Inputs: `--phase` JSON from `direct-flamelet/export_metadata.py`, `--author`
original `thermo.inputData_GRI`, and explicit `--eos SRK|PR`. Outputs: a new
thermophysicalProperties dictionary and a manifest with both input hashes and
all reused author parameters. With no `--out`, the command validates and prints
the plan without writing. Node.js is the only dependency. No secrets/network.

The model is `SRKchungTakaMixture` or `PRchungTakaMixture`, `rfJanaf`, `rfSpecie`,
and sensible enthalpy. This requires the complete matching fork library stack;
the stock-OF8/custom-combustion diagnostic build is insufficient. Its dependent
is the subsequent real-fluid G2 case generator, not the flamelet chemistry.

Optional `--minimum-temperature K` and `--maximum-temperature K` explicitly
extend polynomial inversion bounds. This retains coefficients and records
extrapolation; it does not make
the NASA data experimentally valid at that temperature. A cold-state property
and enthalpy-inversion check must precede a cryogenic-flow claim.

Example:

```sh
node export.mjs --phase phase-metadata.json --author thermo.inputData_GRI \
  --eos SRK --out /results/new-thermo
```

Verification: run the read-only command against the actual 53-species phase and
retained author input. Every species must have seven finite dense-fluid
parameters, positive Tc/Pc/Vc and exactly retained NASA coefficient arrays.
Inspect the written manifest, then qualify actual library loading/properties in
Slurm. A successful conversion is not a property comparison or accepted model.
