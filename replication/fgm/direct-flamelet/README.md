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

## Cold steady branch

`steady_branch.py` runs the discrete scalar dissipations in
`cold-branch-settings.json`, using `cold.json` for the Müller pressure and inlet
temperatures. Each solve starts from a fresh equilibrium initial guess and runs in
its own subprocess with a declared wall-time bound. A difficult near-extinction
case cannot prevent the remaining independent cases. The initial state, raw final
state, available failure state, partial upstream integration exception data, and
individual logs are retained. A timeout is separately recorded in the parent
summary; an interrupted child receipt is not relabeled successful.

```sh
python steady_branch.py --config cold.json --branch-config cold-branch-settings.json --plan
# Add the normal pinned mechanism/source/environment/new-output arguments to run.
```

The upstream returned state is checked with its actual RHS, scaling temperature
by 1000 K and mass fractions by one. Both scaled and dimensional residuals are
recorded. A finite but unconverged profile can be retained for diagnosis but is
ineligible for the physical table. Each exported steady profile has no physical
time coordinate; numerical steady-solver steps are not an unsteady history. An
extinguished converged state is recorded as extinguished, not discarded.
The cold Griffon constant-Cp extension and Cantera polynomial diagnostic properties
remain distinct and visible. These initial 129-point profiles require refinement
or additional branch points where measured discrepancies justify them.

## Discrete energy-index correction

`audit_energy.py` reconstructs the discrete enthalpy balance from a hashed retained
trajectory. It does not solve a new flame. In upstream revision 735711dc, diffusion
uses the full-grid scalar dissipation at interior node i+1, but the extra energy
terms use node i. `spitfire_patch.py` provides a read-only plan and an explicit
apply operation for exactly eight RHS/reference/Jacobian occurrences. It verifies
the upstream Git revision and complete original file hash before writing, and
emits a source-change receipt. Rebuilding the extension remains a scheduled job.
This correction does not make the upstream approximate Jacobian exact.

```sh
python spitfire_patch.py --checkout /path/new-upstream-copy --plan
python spitfire_patch.py --checkout /path/new-upstream-copy --apply --receipt /path/new-patch.json
python unsteady.py --config warm-300.json --integration-config unsteady-settings-257.json --plan
```

Patched drivers require `--upstream-patch-receipt FILE`. Runtime receipts record
that receipt and the actual loaded extension hash, independently of the unchanged
upstream base commit. Unmodified and corrected trajectories remain separate.
The 129/257 comparison starts independently from fresh HP equilibrium at time zero
with otherwise unchanged physical and temporal settings. Chemistry interface checks
remain active. Reduced energy drift requires the physical reruns; source inspection
or retained-state reconstruction alone does not establish corrected convergence.

## Table derivation checks

The original physical fields remain immutable. Table export permits only explicitly
reported negative roundoff up to 2e-10 in non-progress species. It clips those tails
and restores unit mass using the largest non-progress species at each node. It
refuses negative CO/CO2, material negatives, or a total correction above 2e-9.
`composition-projection.json` records every changed node, elemental mole-balance
change, mass/progress changes, and input/output composition hashes. Sources and
temperature are not adjusted or recalculated to hide the change. This narrow export
operation does not establish physical accuracy or change the raw trajectory.
Cold-profile export retains finite temperatures/compositions even if the extrapolated
chemistry evaluator returns nonfinite rates. It lists affected nodes and species,
writes explicit NaN tokens only in those derived CSV fields, and refuses table
qualification. It does not replace nonfinite rates with zero or relax steady residuals.

`table_sensitivity.py` derives new table grids from the same manifest and fixed
whole-frame holdouts. It writes new manifests and receipts, never overwrites the
original. Held-out errors include global physical-peak normalization as well as
the existing near-zero floor. Increasing lookup-grid density cannot repair missing
physical states or a multi-valued progress coordinate.

```sh
python table_sensitivity.py --manifest RUN/family-manifest.json --metadata RUN/phase-metadata.json --source-commit COMMIT --plan
# Add --out NEW_DIRECTORY instead of --plan to derive the four explicit grids.
```

`audit_progress.py --run RUN --out NEW_JSON` measures Cmax relative to the fresh
HP-equilibrium C and repeated-C states on different temporal branches. It retains
folds instead of confusing local eta with Sharma equation 22. It reports actual
trajectory hashes and linear crossing estimates; no reaction sources are invented.
`reexport_trajectory.py --run RUN --mechanism FILE --source-commit COMMIT
--environment-sha256 SHA --out NEW_DIRECTORY` exports every actual accepted frame
and preserves the original whole-frame holdouts. Exact duplicate profiles are
retained on disk but excluded from table training, including copies of a held-out
profile. Use its `--plan` before writing. Apply table sensitivity to the derived
family to distinguish sparse temporal sampling from lookup-grid density. These
tools require NumPy; full state re-export also requires the qualified Cantera and
Spitfire runtime for actual chemistry evaluation.

`cold_rate_probe.py` is a bounded allocated evaluator probe at 85/100/150/300 K,
5.61 MPa, with pure oxygen and an oxygen mixture containing 1e-8 mole fraction
methane. It records the actual patched-runtime identity, all nonfinite outputs,
and reaction 229 arithmetic. A reaction-229-only evaluator isolates that exact
source path; it is not an alternate production mechanism. The command normally
returns success after preserving measurements, including observed failures;
`--require-finite` additionally returns exit 5 for nonfinite Griffon values.
No chemistry source changes are applied. Run its `--plan` first, then use
`--mechanism FILE --mechanism-sha256 SHA --source-commit COMMIT
--upstream-patch-receipt PATCH --out NEW_JSON` in an allocation.
