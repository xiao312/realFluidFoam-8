# Staged SRK flames in Cantera

This module runs Liang Figure 8(a) model stages with Cantera 3.2 FreeFlame.
It owns C++ thermodynamic and transport adapters. It does not claim to reproduce
unpublished PREMIX inputs or resolve the Figure 2 discrepancy.

Inputs: author GRI30 YAML, author species critical data, an ideal flame profile,
case number 1–5, and an explicit output directory. Pressure is 100 atm and
unburned temperature is 298 K. The article does not specify Tu numerically.
Outputs: solved profiles, speed versus refinement, property checks and callback counts.

Cases add SRK density, SRK calorics, Ely–Hanley conductivity, then Takahashi diffusion.
Default kinetics use physical concentrations and NASA reverse constants.
This preserves concentration-law chemistry; fugacity kinetics is a separate option.
SRK chemical potentials support equilibrium checks. Case 2 deliberately retains
ideal calorics and is not a consistent equilibrium model.
An ideal flame supplies a labelled steady-solver guess, not a transient restart.
No OpenFOAM run is resumed by this module.

Cases 1 and 3–5 also calculate HP equilibrium with VCS, checking enthalpy and
element conservation. This diagnostic uses SRK fugacity for the nonideal cases;
it remains distinct from the concentration-law flame kinetics. It does not
replace the saved ideal-profile numerical guess. Equilibrium and flame endpoints
can differ when their chemical equilibrium conventions differ.

Dependencies: pinned Cantera 3.2 C++ SDK, C++17 compiler, `ideal-baseline`, and
`liang-properties/ElyHanley.H`. The latter owns the molar reference-density mapping.
The author critical table approximates Liang's unprovided table.
NO, NO2 and N2O EOS coefficients are zero; transport parameters remain populated.
Original Soave alpha constants are explicit. No coefficient is fitted to flame speed.
Dependents: the Liang comparison report. Production OpenFOAM code does not depend on this module.

All generated state stays in the project directory. No secrets are used.
Linux SDK installation and compilation run in scheduler jobs. Preparation supports
`plan`; existing output paths fail. Source, SDK, input and executable hashes identify each run.

Example: `python prepare.py plan AUTHOR.yaml SPECIES_DICTIONARY PROFILE.csv OUTPUT`.
Use `apply` with the same paths to generate inputs. Then run
`liang-flame INPUTS CASE PHI OUTPUT`, where CASE is 1–5 and OUTPUT is new.

Verification: compile and run `test_srk.cpp`, then execute Case 1 parity and
frozen-state thermodynamic checks before interpreting nonideal flames. Require
Euler identities, pressure-root and finite-difference derivative checks.
Report grid/domain and initial-guess sensitivity separately from model activation.
Successful compilation is not scientific acceptance.

`python check.py RESULT [--ideal-reference-cm-s 7.467003112153642]` reads completed
qualification output. Gates: ideal parity within 0.1%, last grid change below 0.3%,
mass-flux relative range below 0.1%, and species-sum error below 1e-7. These
are numerical screening limits, not evidence of publication agreement.

FreeFlame Newton iterates can contain small negative species fractions. The
conductivity adapter projects its transport-only composition to nonnegative,
normalized fractions and recalculates matching SRK volumes. It does not change
the thermo state or solution fields. Final profiles must have Y >= -1e-9.
The callback report counts these projections and negative partial-volume states.

`prepare_sweep.py plan|apply MECHANISM SPECIES OUTPUT PROFILE_DIR...` prepares
the declared 12-condition phi=0.92–1.44 sweep. Earlier directories win exact
profile ties; the nearest saved phi supplies a numerical guess when necessary.
`plan.json` records target phi and guess phi separately. The inlet uses target phi.
Each stage uses `submit.sh plan|apply ROOT RELEASE SDK INPUTS STAGE BUILD PHI`.

`equilibrium_guess.py plan|apply BASE_INPUTS HP_CSV OUTPUT` builds a separate
temperature/composition ramp from the supplied HP products. It needs Python
Cantera 3.2 for molecular weights. The copied ideal velocity is only a numerical
guess. The generated Qdot column is a placeholder, never a computed heat-release field.
Run this input separately to test initial-guess dependence; retain both results.

`plot.py plan|apply PAPER.pdf RESULTS.json OUTPUT` uses PyMuPDF to preserve the
original panel's physical size, typography and graphics. Its JSON input has a
`results` list with stage, phi and speed_cm_s. It plots only completed points.
The added-data legend identifies all five stages; pending stages remain labelled.
The phi=1.44 endpoint lies outside the printed axes and is retained in the manifest.

`converged_guess.py plan|apply BASE_INPUTS SOLVED_PROFILE OUTPUT` converts this
module's completed profile into another steady numerical guess. It copies the
same mechanism and species table and records hashes of the source profile and
inputs. It does not restart a transient simulation or alter OpenFOAM fields.
Use it for model continuation, retaining the independent ideal-seeded solve.
Verification: the plan must report 53 species and the same inlet composition;
the subsequent solve must pass `check.py` and be compared with independent seeds.

`python collect.py ROOT LEDGER.jsonl` reads scheduler state and completed outputs
without modifying jobs. JSON on stdout contains every job and only numerically
screened points in `results`, ready for `plot.py`. Failed screens retain the
diagnostic text. Run from a contained control directory with Python 3.8+ and
Slurm's `sacct`; the ledger and all referenced jobs must resolve below ROOT.

`sweep.py plan|apply ROOT RELEASE SDK BUILD INPUTS LEDGER STAGE PILOT` submits
the 12 prepared points only after PILOT passes `check.py`. Plan is read-only and
can run while the pilot is unfinished. Apply locks the ledger, skips already
recorded stage/phi pairs, records each successful submission immediately, and
fails if submission output is ambiguous. On Linux it uses `fcntl` and Slurm.
It may run in a short scheduler job with `afterok:PILOT` dependency; failed
qualification prevents submission. No automatic extension of flame jobs occurs.

`paper_stage_check.py RESULTS.json [--require-paper-agreement]` replays the
phi=1.10 comparison from completed, screened results. It checks conservative
visual bounds from Liang Fig.8(a), not exact author data. A failing result is a
publication discrepancy, not proof of an implementation bug. It writes nothing.
Expected for the initial extension: the conductivity increment check fails.

`model-probe INPUTS SOLVED_PROFILE OUTPUT.csv` evaluates identical frozen flame
states at 1 and 100 atm. It compares dilute transport, full Ely–Hanley transport,
the reference-density diagnostic, Takahashi diffusion, SRK concentrations and
reaction rates. It does not solve or alter a flame. Compile `model_probe.cpp`
against the same pinned SDK in a scheduler job. Inputs are read-only; output
must not exist. Dependencies are the existing adapters and shared kernel.
Expected verification: finite properties, unchanged temperature/composition
across each comparison, and explicit ratios separating baseline/model changes
from pressure corrections. Differences are diagnostic, not fitted corrections.

An optional final argument `dense-increment` to the flame executable, job wrapper
or submit wrapper keeps baseline conductivity and adds only
`lambda_EH(T,rho,X) - lambda_EH(T,rho->0,X)`. The dilute evaluation uses 1 Pa
and ideal molar/partial volumes. This is a named sensitivity experiment, not a
claim about Liang's implementation. Default `full` preserves previous results.
The mode is recorded in `model-variant.txt`. The frozen probe reports this
variant and a separate CSV of OH pair contributions when Takahashi collapses.

Diagnostic options are comma-separated: `dense-increment`, `bounded-takahashi`,
and `pressure-chemistry`; `full` selects the unchanged baseline. An optional
following pressure argument is in atm (default 100). The bounded variant limits
pair reduced temperature to [1,5], retaining Cantera's pressure interpolation.
It is an extrapolation sensitivity, not a verified Liang closure. Pressure
chemistry delegates net production rates to a separate ideal phase at identical
T,p,Y, including third bodies and falloff. Only this net-source API is used by
Flow1D; other rate-query APIs on the adapter are not a diagnostic interface.
SRK density, calorics and transport are unchanged. Frozen-state tests compare
every species source with standalone ideal chemistry before flame submission.

`energy-probe INPUTS CASE PROFILE OUTPUT VARIANT ATM` reconstructs midpoint
mixture-averaged diffusion with Flow1D's molar-gradient/mass-correction rule and
writes advective, conductive and species-enthalpy fluxes in W/m2. This continuous
flux reconstruction is a conservation diagnostic, not the exact discrete energy
residual. Compare its variation under grid refinement and against ideal controls.
No source or equilibrium result is fitted to a paper curve.

`prepare_pressure_guess.py plan|apply INPUTS NEW_OUTPUT --atm 1` uses pinned
Python Cantera 3.2.0 to solve a fresh ideal steady control at phi=1.10 and 298 K.
It copies the three model inputs, records hashes and two mesh refinements, and
writes a compatible numerical guess. Run locally or in a compute allocation;
never run the flame solve on an HPC login node. The C++ pilot refines it further.

The plotter optionally accepts a separate `diagnostics` list with phi, stage,
speed_cm_s, pressure_atm=100 and a short label. These use square markers and
separate legends; they never replace default-stage results or connect unlike
model variants into one curve. At most six labelled diagnostic points are shown.

`collect_diagnostics.py ROOT LEDGER.tsv CHECK_SCRIPT` reads the diagnostic pilot
ledger and scheduler once, screens completed results, and emits JSON without
writing remote state. It checks recorded variant and pressure against the ledger.
Inputs and check script must resolve below ROOT; per-job source and input hashes
remain authoritative. Unlike the fixed sweep collector, it retains pressure and
variant labels so sensitivity points cannot be silently combined.

The additional `fine-grid` option appends a third mesh level (slope 0.001875,
curve 0.003125) under the existing 6000-point cap. It changes no model closure.
Use a labelled converged steady guess and compare energy-flux variation with
the two-level result; this is independent of OpenFOAM's original-zero rule.

The sweep accepts `--variant OPTIONS --pressure-atm ATM` (defaults full/100).
Its qualification pilot must match stage, options and pressure. Ledger identity
includes all four of stage, phi, options and pressure; different model curves
cannot silently satisfy each other's entries. The collector verifies the recorded
options and pressure before screening or plotting each completed result.

Verify sweep qualification and duplicate guards on Linux with
`python3 -B -m unittest test_sweep -v` from this module. Tests mock scheduler
submission and require no cluster access; both guards must pass.
