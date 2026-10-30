# Direct methane/oxygen flamelets

This module computes a fresh Cantera counterflow diffusion flame with Cantera's
standard initial guess and automatic solve sequence. It preserves the earlier
`mascotte/flamelet_ch4o2.cpp` driver and its failed runs.

It also provides an independent HP-equilibrium limit along mixture fraction.
That limit is an approximate low-scalar-dissipation comparison for Müller Figure 2.
It is not a finite-rate flamelet, an extinction result, or a valid FGM source table.

## Interface and boundaries

Inputs are a JSON case, a mechanism file with its SHA256, a source commit, and an
environment identity. Output directories must be new. Each output records these
identities and the actual Cantera version. No saved flame or CFD state is loaded.
The finite-rate driver writes all species, temperature, density, heat release,
Bilger mixture fraction, and unnormalized CO2+CO progress and source.
It also exports every species mass-production rate in kg/(m3 s). Heat release
using current species enthalpies and using reference enthalpies at 298.15 K are
separate fields. Their compatibility with an OpenFOAM energy equation must be
checked before use; no extra density factor belongs in the volumetric sources.
`metadata.py` exports the phase's complete NASA7 species coefficients, molecular
weights, species order, and universal gas constant for an audited OpenFOAM
conversion. It uses the same pinned-input CLI and writes `phase-metadata.json`;
this property export is not a simulation or transport qualification.
The equilibrium driver uses linearly mixed inlet mass fractions and enthalpy.
Its endpoints are the original unmixed inlet states.

Dependencies: Python 3.10+, Cantera 3.2, and NumPy. No network, credentials,
OpenFOAM, or scheduler call is made by these scripts. The parent operator submits
all computation through the FlamePilot Slurm adapter. Plotting and independent
scientific acceptance are separate consumers.

The ideal-gas and unity-Lewis assumptions follow the retained Müller flamelet
contract. At 85 K, GRI-Mech thermodynamics require explicit extrapolation.
The cold case records that limitation. This driver does not supply PR-VTA density.
The finite-rate domain and inlet mass fluxes are diagnostic choices, not numbers
claimed to be specified by the paper. Scalar dissipation is measured after solving.

## Usage

```sh
python flame.py --config warm.json --plan
python flame.py --config warm.json --mechanism /path/gri30.yaml \
  --mechanism-sha256 SHA256 --source-commit COMMIT \
  --environment-sha256 SHA256 --out /path/new-output
python equilibrium.py --config cold.json --mechanism /path/gri30.yaml \
  --mechanism-sha256 SHA256 --source-commit COMMIT \
  --environment-sha256 SHA256 --out /path/new-equilibrium-output
```

The plan validates configuration without solving or writing files. Failed solves
leave a failure receipt. No solved profile is exported after a failed solve.
The solver return and its raw YAML state are retained before diagnostics run.
An evaluator failure reports `diagnostic_failed` with `solver_converged: true`
and preserves the raw solution; it cannot qualify the exported physical profile.
`converged_flame` means Cantera returned a burning solution; it does not mean
paper agreement or independent acceptance. Continuity, elemental mixing, enthalpy,
species bounds, and measured scalar dissipation are diagnostics with declared units.
Refinement and comparison runs are needed before scientific acceptance.

## Verification

Run `python -m py_compile common.py diagnostics.py flame.py equilibrium.py` and
both case plans. Then run the warm case in a scheduled allocation and inspect the
actual fields, conservation diagnostics, runtime, and solver return. Test the cold
case independently. A finite-rate and equilibrium comparison is not a substitute
for grid or scalar-dissipation sensitivity.

Primary implementation references:

- [Cantera 3.2 counterflow initialization](https://github.com/Cantera/cantera/blob/v3.2.0/interfaces/cython/cantera/onedim.py#L865-L969)
- [Cantera 3.2 automatic solve sequence](https://github.com/Cantera/cantera/blob/v3.2.0/interfaces/cython/cantera/_onedim.pyx)
- [Cantera Flow1D defaults](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp)

Unlike the earlier Gaussian-kernel driver, this module retains Cantera's coupled
velocity, spread-rate, pressure-gradient, temperature, and species initial guess.
Cold inlet temperature bounds are set explicitly. These differences are hypotheses
for the previous nonconvergence until scheduled physical comparisons test them.

## Physical transient and table route

`unsteady.py` reuses Sandia Spitfire revision
`735711dc4a426cc7504747d732f2e7fcc3db2c23` (BSD-3-Clause), with Cantera 3.2.0
mechanism import. It requires the separately built Spitfire extension and SciPy.
It first qualifies imported finite-rate chemistry against Cantera, solves an
independent moderate-dissipation control, then integrates a fresh HP-equilibrium
profile from physical time zero at the configured Peters scalar dissipation.
No saved steady or CFD state initializes the transient. The settings are diagnostic
choices, not numbers fitted to the paper. Width and inlet mdot in the shared case
are unused by this mixture-fraction solver.
The moderate control has bounded iterations and an independently reported RHS
residual. Its failure is retained and does not prevent the independent transient.
If Spitfire raises an integration exception with partial times/states, those raw
arrays are saved under an explicitly partial filename before reporting failure.

```sh
python unsteady.py --config warm-300.json --integration-config unsteady-settings.json --plan
# Add the same pinned mechanism, source, environment and new output arguments as above.
```

The actual mixture-fraction equations evolve species and temperature at constant
pressure, unity Lewis number, and adiabatic boundaries. Variable heat capacity and
enthalpy-flux transformation terms are enabled. Boundary streams fix the linear
mixed enthalpy. This uses Spitfire's physical ESDIRK time integration, not Cantera's
pseudo-time steps used during its steady solve. See the upstream
[flamelet demonstration](https://github.com/sandialabs/Spitfire/blob/735711dc4a426cc7504747d732f2e7fcc3db2c23/docs/source/demo/flamelet/introduction_to_flamelets.rst)
and [implementation](https://github.com/sandialabs/Spitfire/blob/735711dc4a426cc7504747d732f2e7fcc3db2c23/src/spitfire/chemistry/flamelet.py).

Raw time histories are saved before diagnostic export. The driver verifies actual
final time because upstream can return at its step cap. A temporary observer wraps
the upstream accepted-step callback, records negative-species clipping and its
elemental corrections, and restores the original callback interface afterward.
The observer does not change the upstream clipping operation. Elemental mixing,
enthalpy and mechanism-rate discrepancies are measured on exported states.
Griffon uses constant-Cp extension below species Tmin; this differs from Cantera's
NASA polynomial extrapolation. The first control uses both streams at 300 K.

`table.py` consumes hashed finite-rate profile receipts and exact phase metadata:

```sh
python table.py --manifest RUN/family-manifest.json --metadata RUN/phase-metadata.json \
  --source-commit COMMIT --plan
# Replace --plan with --out NEW_TABLE_DIRECTORY to write physical.tbl and diagnostics.
```

Its `direct-flamelet-family/v1` manifest contains `metadata_sha256`, `z_points`,
`eta_points`, and `members`: each has `id`, `directory`, `receipt_sha256`, and role
`training` or `held-out`. It refuses duplicated physical files, mismatched
mechanisms/inlets, and inconsistent progress coordinates. It writes the agreed
`forge-fgm-table-v2` interface with all species, volumetric CO2+CO source, formation
heat source, and diagnostic temperature. OpenFOAM transports raw CO2+CO mass
fraction; only lookup uses eta between the measured Cmin(Z) and Cmax(Z).
Degenerate pure-stream rows have no independent progress coordinate. Out-of-band
queries are refused. Equilibrium-only outputs cannot enter this table.
The Python held-out diagnostic allows a 1e-12 floating-point endpoint excursion and
uses a 1e-12 degenerate-span threshold. The C++ strict default has no endpoint
tolerance and only treats exactly zero span as degenerate. These admissibility
rules are explicitly different; they are not claimed to be identical runtime tests.

Whole physical frames and every fifth interior profile point are held out. Reports
include coverage refusals, source sign disagreements, absolute errors, and relative
errors with explicit floors; no arbitrary all-pass verdict is produced. A single
trajectory does not qualify interpolation across dissipation histories.

Sharma Figure 1/2 (PDF pages 6-7, SHA256
`65ae91e8734d8006f4274c70f548f969ab18ca698d8aad8d3b3384882356349c`) uses 60 bar,
Kong's detailed mechanism, and unsteady diffusion flamelets. The initial GRI/5.61
MPa library is a G2 interface diagnostic, not a reproduction of Sharma. Sharma's
normalized CO2+CO progress differs from the local table eta. A full paper comparison
also needs intermediate-progress coverage, the mechanism and boundary conditions,
and the relevant presumed-PDF/enthalpy treatment.
