# Staged SRK flames in Cantera

This module runs Liang Figure 8(a) model stages with Cantera 3.2 FreeFlame.
It owns C++ thermodynamic and transport adapters. It does not claim to reproduce
unpublished PREMIX inputs or resolve the Figure 2 discrepancy.

Plot input JSON can include `stage_labels`: five nonempty strings in stage order.
Use explicit labels when a displayed curve changes model variants, such as the
corrected Takahashi Table 2 coefficient. The plot manifest records these labels.
This presentation option does not change calculated data or comparison criteria.

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

Case 5 diffusion diagnostics add two opt-in choices. `takahashi-bulk` uses
whole-mixture mole-weighted critical temperature and pressure for every binary
pair, instead of Cantera's pair-normalized mole weights. It requires the bounded
and Table 2 options. This tests the base-gas interpretation of Takahashi's
correlation; it is not established as Liang's implementation. `mass-gradient`
selects Cantera's mass-fraction-gradient mixture diffusion formulation, including
its corresponding coefficients. Default flames retain mole-fraction gradients.
Neither option changes chemistry, calorics, or conductivity.

`soret` selects an additional methane sensitivity control using Cantera 3.2's
inherited mixture-averaged thermal-diffusion coefficient. It is not the older
PREMIX light-species approximation or an identified Liang setting. Case 5
passes the Takahashi-corrected mixture coefficient into this calculation while
its collision terms retain dilute binary coefficients. This hybrid closure
requires a distinct model label; it never replaces the no-Soret baseline.

`SoretCompatibleFlow` retains the true `liang-staged` identifier and native
Cantera transport, flux and energy routines. Its only compatibility adaptation
is the pinned `_finalize` identifier check. For an explicitly verified
`StagedTransport` instance, it disables the flag during that setup-only method
and restores it on every exit. It rejects unsupported custom transports.
There is no SDK patch, transport-name substitution, extra enthalpy flux, or
change to coefficients. The saved flow still records Soret as enabled.

`test-soret INPUTS SOLVED_PROFILE` independently reconstructs thermal
coefficients from viscosity, binary diffusion and collision integrals. It
checks the Case 5 projection, dilute pressure independence, zero summed
coefficient, actual Flow1D flux direction and mass closure, and the custom
finalization path. The build must pass these checks before a Soret flame.
The existing SDK, compiler and immutable input table are its dependencies.
Inputs and output logs follow the same project-root boundary; no credentials
or new service is involved. See the
[source audit](../../docs/liang-soret-control-audit-20261021.md) for equations
and limits. Example: `test-soret inputs result/profile.csv`; expect all checks
to pass with relative coefficient errors below `1e-10`.
The test accepts either the named initial-profile schema or an exported solved
profile. Soret solves also write `soret-flux.csv` with each face's actual native
coefficient, ordinary flux, thermal flux, total flux and partial enthalpy.
Units are explicit in the column names. New jobs retain observed executable,
source, command, build and SDK records, with an explicit 3072 MiB allocation.
The separate `energy-probe` rejects `soret`: its reconstruction has no thermal
diffusion term. Use the recorded native face flux for a Soret energy audit.
Applying its no-Soret reconstruction would omit both thermal mass flux and
the associated diffusive enthalpy flux.

`analyze_soret.py plan|apply OBSERVATION.json FLUX_DIRECTORY NEW_OUTPUT`
compares the six completed methane controls: Cases 1, 4 and 5 with Soret off/on.
Its `inspect_native_fluxes` helper exposes measured residuals after validating
file structure, coordinates and finite data. The hydrogen diagnostic uses it
to preserve failed strict checks for investigation. The existing `native_fluxes`
entry point and methane CLI retain all original strict tolerances.
The observation must include passed numerical screens, output hashes and
the local profile snapshot. The flux directory contains each on-run's
`jobs/JOB/result/soret-flux.csv`. It validates hashes, face coordinates,
species order, mass-flux closure and thermal/ordinary decomposition.
Output contains paired speeds, per-species flux summaries and native
face enthalpy-flux components. These are diagnostic fluxes on each solved
profile; they do not isolate the full speed response at a frozen state.
It uses Python, NumPy and collected files only. No remote writes, model changes,
credentials or plotting dependencies are involved. The comparison report consumes
its output. Run `plan`, then `apply` to a new directory; expect all native
flux identities to pass. Scientific agreement is reported separately.

The additional `manual-soret` diagnostic uses the published CHEMKIN
light-species formula, with direct evaluation of the fixed TRANFIT collision
polynomials. It enables Soret and replaces only the thermal coefficient.
It is mutually exclusive with `soret`, which keeps Cantera 3.2's formula.
The model selects molecular weights below 5 kg/kmol and applies a zero-total-
mass-flux projection. It uses the selected stage's mixture diffusivity and
physical density. That dense thermal closure is a declared sensitivity
assumption, not a high-pressure thermal-diffusion validation.
The ordinary diffusion stencil, chemistry and energy equation remain unchanged.
No source coefficient is fitted to a paper flame speed.
This first methane control has no Burke author-pair override.
The archived preprocessor sign disagrees with the published manual; this
diagnostic follows the manual's sign and does not claim exact historical
PREMIX equivalence. See the
[source review](../../docs/liang-legacy-soret-implementation-review-20261021.md).
Its dependencies are the existing transport adapter and pinned SDK.
The build checks the binary light-species sign, permutation, absent-species
limit, zero coefficient sum, pressure scaling and native-flow flux direction
before any diagnostic flame can run.

`diffusion-probe INPUTS PROFILE NEW_OUTPUT.csv` audits frozen profile states with
pair and bulk critical-property averaging. It independently reconstructs
`D_i = (1-Y_i)/sum(j!=i, X_j/D_ij)` from the returned binary matrix, checks matrix
symmetry, and writes species diffusivities and corrected fluxes for both gradient
bases. It uses the existing SDK and adapters, has no new dependencies or secrets,
and never changes the input profile. Compile it with the existing build job.
For example, run `diffusion-probe inputs result/profile.csv diffusion.csv` in a
compute allocation. Expected: reconstruction error below 1e-10 and zero net
diffusive mass flux to floating-point accuracy. Passing these checks validates
the conversion, not agreement with Liang. The energy probe supports the same
options so a diagnostic flame cannot silently be analysed with another closure.

The diffusion probe also reports a frozen-state nonideal-driving-force
diagnostic. At each face it evaluates the two composition states at the same
midpoint T and fixed p, then adds `X_i*d(log(phi_i))/dx` to `dX_i/dx` before
the usual zero-mass-flux correction. This follows the constant-temperature
chemical-potential derivative in [Giovangigli et al. (2011), Section 4.2](https://www.cmap.polytechnique.fr/~giovangi/688.pdf); it
does not introduce a temperature-gradient/Soret term. New columns report the
corrected flux and its difference from the baseline. Both retain zero net mass
flux. No flame equation or baseline model changes. The cited full transport
model is not evidence that Liang used this closure with Takahashi coefficients.
The SRK unit check includes the constant-TP Gibbs–Duhem constraint on these
composition derivatives.

`figure_gallery.py` accepts an optional `--diagnostics FILE`. This JSON contains `diagnostics`
and `baseline_sha256`, which must match the baseline Cantera input file.
Each entry must identify stage, phi, speed, label, 100-atm pressure, a completed
job and a passed numerical screen. These appear only in the corresponding
per-case panel as unconnected symbols. Up to eight diagnostic series per case
use distinct color/marker combinations with matching legends.
Baseline overview curves remain the
declared 65-point calculation; a sensitivity point cannot replace a curve.
The legacy `diagnostics` member in the baseline JSON belongs to `plot.py` and
does not silently add experiments to this seven-panel gallery.

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
The shared kernel also exposes a separately selected signed-factor continuation.
The H2 driver uses it to test the pinned upstream OF6/OF8 polynomial mixing.
`signedAlpha` and `smoothedAlpha` are mutually exclusive and must be set before
evaluating a state. The signed option propagates through phase, transport-state
projection and pure-species energy diagnostics. `test_signed.cpp` checks
negative/zero mixture sums, polynomial equivalence, thermodynamic derivatives
and pure-fluid parity; `test_srk.cpp` covers all three continuations.
This option does not change the default methane driver or identify Liang's code.
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
the conditions declared in INPUTS/plan.json only after PILOT passes `check.py`. Plan is read-only and
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

`paper_reference.py plan|apply PAPER NEW_JSON` extracts raster figure coordinates
from the pinned Liang PDF using PyMuPDF and NumPy. The affine calibration
uses measured axis tick centers; red/up and blue/down triangle centers give
Cases 3/4. The connected blue curve gives Case 5. Black curve/diamond overlap
limits separation of Cases 1/2; those references carry larger uncertainty.
These are digitized image coordinates, not author numerical data. Extraction
retains pixel coordinates, calibration and explicit uncertainty for audit.
The paper marker near phi=1.02 is included in addition to the earlier sweep grid.
`compare_reference.py RESULTS_JSON REFERENCE_JSON` reports per-point differences
and per-stage RMS/max errors. Its predeclared comparison screen is max(0.05 cm/s,
1% of reference) plus image uncertainty. It never extrapolates and compares
marker series only at matching nominal operating conditions. A screen pass
does not establish scientific acceptance or identify unpublished author models.

`alpha-probe SPECIES.txt PROFILE.csv NEW_OUTPUT.csv` checks the existing SRK
kernel at each in-flame zero of the Soave square-root factor. It freezes the
nearest saved composition and evaluates departure enthalpy on both sides with
shrinking temperature offsets. A finite limiting jump distinguishes a closure
non-smoothness from ordinary heat capacity. This standalone C++17 diagnostic
needs no Cantera SDK, changes no solver model and writes only the new output.

`smoothed-alpha` selects the separately labelled Giovangigli high-temperature
extension documented in `docs/cantera-alpha-discontinuity-20261020.md`. It changes
SRK attraction and all its derivatives consistently, including transport-only
projected states. It is not a verified Liang closure. `test_alpha.cpp` checks
enthalpy integrability across the original species crossings; the legacy model
must reproduce the failing control. `test_srk.cpp` checks both variants' EOS,
Cp, partial enthalpy and fugacity identities away from and at smooth crossings.

`takahashi-table2` corrects only the Pr=3 row exponent B from Cantera 3.2's
3.39031 to 2.39031, verified in Takahashi Table 2, printed page 419, and Nguyen's
`chungTakaTransportI.H`. Use together with `bounded-takahashi`; the existing
bounded control remains unchanged. `TakahashiTable.h` computes the difference
of that row and its interpolation weight, leaving all other coefficients and
limits intact. Build verification checks the actual Cantera function against
the primary row at Tr=2, outside-interval parity, and pressure continuity.

`prepare_sensitivity.py plan|apply BASE NEW_OUTPUT extended-domain|shifted-guess`
prepares a labelled steady FreeFlame numerical sensitivity input. Domain extension
doubles the width by adding flat inlet/outlet regions while preserving every
original interior point. The shifted guess keeps the original domain and moves
the profile by one eighth of its width; its velocity guess is 25% higher.
Mechanisms, model table and physical inlet state are unchanged. Neither mode
creates CFD fields or permits a transient restart. Output must not exist.
The provenance file records all source hashes and transformations. Verify finite
data, increasing coordinates and species normalization, then compare converged
speeds with the same model/options and refinement criteria. These sensitivities
must not be represented as additional operating conditions.

`energy_audit.py plan|apply ROOT BUILD SDK MANIFEST NEW_OUTPUT` runs the existing
energy probe on frozen profiles in a scheduler allocation. MANIFEST is a JSON
list of `profile_job`, `stage`, `variant`, `pressure_atm`, and absolute `inputs`.
All paths must be inside ROOT; output belongs to the current Slurm job. Plan is
read-only. The apply path verifies the energy binary hash, rejects existing
output, and records profile/input hashes, flux range, endpoint difference and
diffusive mass-flux closure. This is a reconstructed face flux, not the exact
discrete Flow1D residual. Compare identical models across refinement levels.

The energy probe also reconstructs a separately labelled pure-species enthalpy
diffusion flux. Liang p.1734 applies the departure formula to individual species
and distinguishes their mass-weighted enthalpy from mixture enthalpy. This makes
pure-species versus partial-molar diffusion enthalpy a testable interpretation,
not a confirmed implementation detail. The probe holds the saved flame, mixture
enthalpy, chemistry and transport coefficients fixed and changes only the
enthalpy multiplying each diffusive mass flux. It never changes the phase's
thermodynamic API or a flame solution. In the ideal case both fluxes must agree.
`pure_species_total_W_m2` and `pure_minus_partial_W_m2` expose this diagnostic;
the existing `total_W_m2` remains the partial-molar reconstruction.

`total-enthalpy` selects an experimental free-flame energy residual from the
divergence of total enthalpy flux: upwind advective mixture enthalpy, centered
heat conduction and face species diffusion enthalpy. Chemistry has no separate
energy source in this total-enthalpy balance. The optional `pure-species-flux`
changes only diffusion enthalpies to pure-species values; it requires
`total-enthalpy`. Mixture enthalpy, Cp, equilibrium and kinetics retain their
existing APIs. Neither option is a verified Liang implementation.

This diagnostic follows the interpretation supported by Liang p.1734 and
Jorda Juanos/Sirignano (2017), p.57, which evaluates species enthalpies with
individual-species parameters. Source: https://doi.org/10.1016/j.combustflame.2017.01.030
(author copy: https://sirignano.eng.uci.edu/theme/pdfs/39.pdf).
The partial-molar total-enthalpy control separates this flux choice from changing
the energy discretization. Pseudo-time stepping retains Cantera's T relaxation
term solely to find a steady solution; it is not a physical transient reactor.
Only free flames without radiation/two-point control are supported. Qualify with
an ideal control, refinement, and the reconstructed upwind total-flux balance
before comparing nonideal pilots. All options remain disabled by default.

The same frozen-profile energy audit compares the native CFD energy-flux
closure (raw non-inert diffusion velocities, with nitrogen balancing their sum)
against the mass-fraction-weighted correction used in the species equations.
`inert_minus_mass_corrected_sensible_W_m2` quantifies only this closure difference with
identical coefficients and enthalpies. A nonzero value is a consistency diagnostic,
not a measured flame-speed effect. This audit does not change running CFD cases.
Species enthalpies in this closure check subtract ideal NASA formation enthalpies
at 298.15 K, matching the sensible-enthalpy CFD convention. They are separate from
the absolute enthalpies used in the total-energy reconstruction.

`takahashi-high-t` is a diagnostic that removes only the reduced-temperature
upper clamp at 5, retaining the lower clamp at 1 and requiring both
`bounded-takahashi` and `takahashi-table2`. This tests an implementation detail
not specified by Liang. Takahashi's fitted data mostly cover Tr=0.95–5; using
the correlation above that range is extrapolation, not an accepted correction.
The frozen-state probe reports H2, OH and CH4 diffusivities with and without
this upper clamp before any flame comparison. All other models remain fixed.
## Figure 8(a) comparison gallery

`figure_gallery.py plan|apply PAPER CANTERA REFERENCE CFD_AUDIT SWEEP_AUDIT OUTPUT`
creates seven separate comparisons: Cantera overview, developed-solver CFD
overview, and one comparison for each Case 1–5. Each has the original 204 by
175 point paper panel and caption beside the computed panel. Inputs are frozen
JSON results, digitized paper data, and validated front-history audit summaries.
Outputs are PNG/PDF pages, a combined PDF, and an input-hash manifest. The
renderer uses PyMuPDF and the existing axis calibration. It submits no jobs.
Diagnostic points with the same case and label share one marker and legend;
different operating conditions remain unconnected. Duplicate points at the same
case, label and equivalence ratio fail as ambiguous input.
Missing CFD stages remain explicitly pending. CFD markers are latest valid
temperature-front estimates, not accepted steady flame speeds. Other OpenFOAM
solvers appear only in the individual Case 1 comparison. Verify the seven-page
count, series inclusion rules, source hashes, and rendered labels before upload.

Native profile and Soret face CSVs use `double::max_digits10` (17 significant
digits). This serialization change preserves binary coordinate/temperature
values during offline reconstruction of thin-grid gradients. It changes no
transport coefficient, residual or convergence criterion. Older 16-digit exports
remain historical evidence and retain their measured reconstruction limits.
