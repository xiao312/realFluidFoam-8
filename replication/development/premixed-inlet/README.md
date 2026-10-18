# Inlet–outlet premixed benchmark draft

Prepare a single planar CH4/air front with unburned mixture in the left half
and adiabatic equilibrium products in the right half. Cold gas enters on the
left; products leave on the right. The inlet speed is an explicit initial guess,
not a flame-speed measurement. The front may drift either way depending on the
guess. This follows the DeepFlame topology; it differs from the paper's central
ignition/two-front method, which remains a separate comparison.

Inputs: `cases.json`, pinned GRI30 thermo/reaction files and a generated seed.
The schema records phi, pressure, unburned T, length, cells, inlet-speed estimate,
initial dt, maxCo/maxDeltaT, end time and write interval. Outputs: fresh case,
input hashes, seed provenance and endpoint diagnostics. `plan` is read-only;
`apply` refuses existing output. All state stays below the project workspace.
No credentials. Dependencies: existing generators, OF8/library build, Python 3;
seed preparation alone requires Cantera 3.2.0. Solver runs use the real-fluid
library and original chemistry, with no Cantera/DNN runtime dependency.
Dependents: draft comparison runner and flame-speed analysis.

`equilibrium.py` constructs ideal-gas NASA7 species from the exact pinned author
coefficients and uses Cantera HP equilibrium. Elemental compositions come from
Cantera's GRI30 species definitions. Mole fractions are converted using the
author's molecular weights. This is an **ideal-gas equilibrium seed**, not a
claim of SRK fugacity equilibrium or real-fluid HP conservation. Record the
transition to real-fluid thermodynamics and require seed-independence before
acceptance. This explicit approximation must not be silently promoted.

Pressure is zeroGradient at the inlet and waveTransmissive at the outlet, with
gamma evaluated from the hot mixture by the actual library. T/species/U are
fixed at the inlet and zeroGradient at the outlet; transverse patches are empty.
Initialize U so rho*U is equal on both halves, using densities from the runtime
library probe. The discontinuity is at L/2; no artificial hot ignition kernel.
Two initial speed guesses at phi=1.10 test sensitivity to imposed inflow.

The 18 October replacement sweep uses `phi-090-liang` through `phi-140-liang`
in 0.05 equivalence-ratio increments at the same 100 atm / 298 K condition.
`liang-inlets.json` records approximate inlet guesses from the black Liang curve
in Nguyen 2022 Figure 12, not Nguyen's red-square results. The displayed curve
starts near phi=0.920: phi=0.90 is explicitly a short secant extrapolation.
The prescribed inlet is only a guess; gas-relative flame displacement remains
the measurement. Each new condition requires its own renamed/upstream startup
comparison before a fresh full run. Previous 0.10/0.20 m/s cases remain historical
inputs, but their running allocations are cancelled at the owner's request.
`digitize_liang.py PDF OUTPUT` is a local, read-only PDF extraction with an explicit
output directory; it uses the existing analysis environment's PyMuPDF/numpy.
It refuses existing output and verifies the inspected vector path and axis extent.
The original PDF and full extracted curve stay outside Git. The small inlet
table is a numeric input with its digitization provenance, not reference truth.

Example: `python prepare.py plan phi-110-u010 OUTPUT smoke`.
Generate seeds locally with `equilibrium.py apply SEED_DIR`; pass that directory
to prepare's `--seeds`. `runtime.py finalize CASE` reads the density probe and
finalizes U/gamma; `runtime.py check CASE` validates all written species and rho.
Smokes advance 2 microseconds. They qualify initialization/build only; full
development runs target 1 ms and require passed startup evidence.
Full submission uses `submit.sh plan|apply ROOT IMAGE RELEASE KEY full SMOKE_ID`,
verifying identical configuration, seed and solver source plus renamed/upstream
field agreement. It builds in a new job and reserves 4 cores for at most 48 hours.
These are development allocations; no automatic convergence acceptance or extension.

Verification: syntax/plan, normalized and element-conserving seed, exactly half
the cells in each state, fixed boundary composition and mass-consistent U, then
scheduled checkMesh/finite-species checks. Compare renamed/upstream executables
on identical cases. Flame speed requires gas-relative OH displacement or a
species-consumption balance, plus steady-profile, mesh/time/domain/seed checks.
Do not report imposed inlet speed as the computed burning velocity.

