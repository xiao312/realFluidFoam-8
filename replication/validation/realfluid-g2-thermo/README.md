# Real-fluid thermodynamic input adapter

`estimate-kong-parameters.mjs --base-manifest FILE --transport CHEMKIN_FILE`
provides a read-only plan for the missing CH3O2 parameter block. Optional
`--out NEW_DIR` writes a separate augmented parameter input and receipt, never
the base manifest. All existing parameters are retained exactly. CH3O2 uses
the author-deposited transport epsilon/sigma, the Smit LJ Tc/Vc approximation,
and SRK Zc=1/3 to derive Pc. Acentric/association factors are explicitly zero
in this spherical-LJ approximation; dipole comes from the transport file.
Fuller diffusion volume is additive from the existing author C/H/O increments.
This is an estimated radical input, not a measured critical state or proof of
Sharma's implementation. It adds no kinetics and fits no paper data.
Dependencies remain Node built-ins; no credentials/network. Verify source
hashes, unchanged existing entries and Tc/Pc/Vc dimensional consistency, then
use `export.mjs` with the actual Kong phase. Actual library properties and
source/enthalpy coupling require separate allocated qualification. Background:
[Smit1992](https://doi.org/10.1063/1.462271) and
[SDToolbox Section9, critical-property estimates](https://shepherd.caltech.edu/EDL/publications/reprints/ShockDetonation.pdf).

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


Optional `--srk-root-selection largest|homogeneousGibbs` defaults to largest.
The explicit homogeneousGibbs mode writes one consistent per-species EOS policy
and records it in the manifest. It is available only for SRK and requires the
matching rebuilt full runtime. It selects the lowest homogeneous Gibbs root,
not mixture VLE. No NASA/critical coefficient or transport model changes. Verify
default output dictionary parity and declared policy before captured-state and
fresh-CFD qualification; never apply it to evolved fields or claim flash results.

`probe/plot-captured-gaps.py --results COLLECTED_QUERY_DIR [--out NEW_DIR]` plots actual executing-library Hs(T) samples at captured/nominal pressure and a microkelvin view of the selected-root jump. No output is the read-only plan. It requires two explicitly named captured point JSONs and CSV query outputs; file hashes are retained. It does not interpolate across the measured jump, normalize composition, fit a curve, change an evaluator or infer VLE equilibrium. Outputs PNG/SVG and an evidence JSON under a new directory. Optional plotting dependencies are Python/Matplotlib/NumPy; exporters and native queries retain their existing interfaces. Verification: plan then render the independently retained C03/C05 queries and visually inspect gap/target/units; a visualization is not a CFD pass.
