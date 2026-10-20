# Liang hydrogen Figures 2–7

This module reconstructs the hydrogen calculations in Liang, Li and Law (2019),
DOI 10.1016/j.proci.2018.06.070. It uses the cited Burke et al. (2012) mechanism,
not Cantera's bundled `h2o2.yaml`. It does not change production CFD solvers.

## Inputs, outputs and configuration

`acquire.py plan|apply OUTPUT [--source-dir ORIGINALS]` downloads or reads
hash-pinned author kinetics, transport and CTI, performs strict Cantera 3.2
conversion, extracts the pair polynomials and compares both author formats at
54 prescribed states. It records the known malformed bibliographic-note repair.

`prepare.py plan|apply MECHANISM SPECIES_TABLE OUTPUT` validates a 13-species,
27-reaction author mechanism and a previously qualified SRK parameter table.
It writes immutable ideal/SRK YAML inputs, species parameters and a provenance
manifest. Downloaded author files stay outside public Git; their redistribution
license is not established. Source URLs and hashes are in the mechanism audit.
With `--pairs AUTHOR_PAIR_JSON`, preparation includes the ten applicable
quantum binary-diffusion polynomials in the author's appended transport block.
`HydrogenTransport.h` replaces those pressure-scaled binary coefficients before
mixture averaging and Takahashi correction; other pairs retain LJ transport.
Without `--pairs`, preparation makes an explicitly named LJ control.
Liang does not state whether his calculations enabled this author extension.
The polynomial temperature validity interval is not stated in the source.

`prepare.py --pairs AUTHOR_PAIR_JSON --thermal-pairs` additionally writes
`collision-pairs.txt` from that same source. Its ten unordered pairs must match
`pairs.txt`. Each row contains two names followed by four A*, four B* and four
C* coefficients. These dimensionless cubics use actual `ln(T/K)`, without
exponentiation. The manifest records both the source and sidecar hashes.
The default preparation remains unchanged.

The named `soret-baseline` and `manual-soret-baseline` controls enable native
thermal mass flux and its associated enthalpy flux. Both retain the baseline
energy equation, chemistry, ordinary stencil and refinement. Other option
combinations are rejected in this first qualification.
`soret-baseline` uses Cantera 3.2's mixture-averaged formula.
`manual-soret-baseline` uses the published manual's light-species formula with
the author A*/B*/C* pairs and the existing fallback for unlisted pairs.
The manual control requires the explicit collision sidecar; missing, duplicate,
nonfinite or mismatched pair records fail before solving.
The selected-stage mixture diffusivity still includes the same author D pairs
and, in Case 5, the same Takahashi correction.
The final mass projection preserves zero total thermal mass flux.
Neither formula is established as Liang's setting or validated as dense-gas Soret.
Author collision-fit validity bounds are unknown, including the 298 K inlet.

Both controls save actual native face coefficients and thermal/ordinary fluxes
to `soret-flux.csv`. Configuration and callback records identify the formula,
pair count and sampled temperature range. Old no-Soret inputs remain readable.
The dependency is the existing `cantera-liang` formula and flow wrapper; no
production CFD code consumes the sidecar.
`test-soret INPUTS FIXTURES.csv` checks independent author/fallback fixtures,
binary scaling, ordinary-transport invariance, stage selection, pair parsing
and native flux direction/closure before the build qualifies.
The committed `soret-fixtures.csv` contains 15 independent evaluations from
the raw author appendix and published fallback. It covers H2/N2, H/N2,
H2/O2, H/O2 and H2/Ar at 298, 1000 and 2500 K.
The [fixture source record](../../docs/liang-hydrogen-soret-integration-review-20261021.md)
pins raw data, mechanism weights and the independent evaluation script.
Both Soret modes require a build that passed this additional test.
The completed-run ledger's v3 schema includes observed configuration fields
and hashes the native thermal-flux CSV when Soret is enabled.
It rejects missing or unexpectedly enabled thermal-flux output.
Existing no-Soret configurations remain readable.
Example: `flame inputs 3 1.4 new-result - .01 298 manual-soret-baseline 1`.
Use the same source and inputs with `baseline` for its paired no-Soret control.
Preparation supports `plan`; Slurm still owns compilation and flame solves.

`analyze_soret.py plan|apply MANIFEST REFERENCE_JSON NEW_OUTPUT` requires complete
off/native/manual triples at each case and equivalence ratio. It verifies
matched source, executable, input records, domain and inlet conditions, applies
the existing numerical checks, and audits native thermal flux using the shared
`cantera-liang/analyze_soret.py` reader. Its CSV and JSON report changes in speed,
the unchanged Figure 3 comparison screen, and source/output hashes. Missing
paper points remain missing; no extrapolation or parameter fitting is performed.
It depends on NumPy and these local analysis modules, with no network, secrets
or solver mutations. Run `plan` before `apply`; numerical checks must pass.
Strict native-flux residuals and their failures remain explicit in the result,
with no tolerance change. Paper agreement remains a separate outcome.
`soret_roundtrip.py plan|apply MANIFEST NEW_JSON` investigates those failures
using the writers' 16-significant-digit decimal rounding bounds. It reports
whether thermal-flux reconstruction differences fit that bound, plus measured
face composition and coefficient sums. It neither changes the strict audit nor
normalizes saved data. The manifest must contain completed Soret runs; NumPy
and the shared native reader are the only analysis dependencies.
`test_soret_roundtrip.py MANIFEST NEW_FIXTURE_DIRECTORY` uses the captured rich
Case 3 manual control: expect its reconstruction error to fit the decimal bound
and an injected 100 ppm flux error to be detected. Fixtures stay outside Git.

`compare_domains.py plan|apply MANIFEST.json NEW_OUTPUT` reads completed,
matched source/input runs at three or more domain lengths. It verifies actual
profile lengths against configuration and the existing numerical screens.
It writes speed, endpoint-temperature and boundary-tail spans with input hashes.
Group identity includes case, phi, transport and model variant.
This offline diagnostic uses the existing NumPy profile checks and run records.
It makes no remote writes, modifies no inputs and does not introduce a new
paper acceptance tolerance. Expected result: all numerical checks pass, with
observed domain sensitivity reported separately from paper agreement.

`flame INPUT CASE PHI OUTPUT [GUESS|-] [WIDTH_M] [TU_K] [VARIANT] [GRID_FACTOR]`
runs 100-atm H2/air.
Cases are `1`, `2`, `3`, `3star`, `4`, and `5`. Cases 3–5 initially use the existing
total-enthalpy residual; baseline 3star uses stock Cantera's partial-enthalpy
temperature residual and is not established as Liang's Case 3* implementation.
Nonideal chemistry uses the pressure-based adapter. Case 4/5 conductivity is the
explicit dense-increment diagnostic, not a verified reconstruction of Liang's
unpublished rich-H2 mixing modification. Case 5 uses bounded, Table-2-corrected
Takahashi binary diffusivities with mixture-averaged mole-gradient fluxes.
The optional outer prefix `concentration-` retains the phase's existing actual
SRK concentration mass-action law instead of installing the pressure adapter.
It also changes third-body and falloff concentrations; standard reverse
equilibrium constants remain those of the inherited ideal reference phase.
This is a distinct kinetic diagnostic, not an energy correction or an identified
Liang closure. It must precede any `midpoint-` and `smooth-` prefixes.
Alternatively, the outer prefix `activity-` enables symmetric fugacity-based
mass action, `c_activity = X*p*phi_fugacity/(R*T)`, for both forward and reverse
rates. Third-body/falloff collisions retain physical SRK concentrations.
Standard-state reverse equilibrium constants remain ideal; applying a second
fugacity correction there would double count it. This is a named interpretation
of Liang reference 10, not an identified Liang/Burke collider implementation.
It supports Case 1 parity and thermodynamically complete Cases 3–5; Case 2
is rejected because its density-only ablation lacks consistent activities.
`activity-` and `concentration-` are mutually exclusive.
The configuration records the selected law and the completed run records the
pressure-adapter callback count (zero when the adapter is not installed).
Soret and radiation are disabled; the paper does not specify them.
Default Tu=298 K is an assumption, not a reported value.
The default `baseline` uses partial-molar species enthalpies in diffusion.
`pure-flux` instead uses pure-species SRK enthalpies there, reflecting Liang's
statement that mixture enthalpy differs from the mass-weighted species sum.
This is a named paper interpretation, not a change to the phase's thermodynamic
partial-molar API. `full-conductivity` uses the full unmodified Ely–Hanley model;
`pure-flux-full-conductivity` combines the two for a controlled diagnostic.
`matched-energy` uses total enthalpy with the same upstream advection stencil
as the species equations; `pure-flux-matched-energy` also changes diffusive
species enthalpies to their pure values. `pure-temperature` implements the
pure-species temperature approximation in Liang reference 8, including
Cp=sum(Y Cp_pure). Each energy variant is also usable with ideal Case 1 for
parity and grid tests. `EnergyFlows.h` owns these isolated energy residuals.
`cp-only-temperature` tests the narrower wording of Liang's dissertation,
Chapter 8, page 169: Case 3* updates heat capacities. It retains the SRK mixture
Cp in the temperature residual but uses ideal-reference species enthalpies for
reaction and diffusion terms. Density and pressure-based chemistry remain as
configured. This is an explicitly inconsistent thermodynamic approximation,
not a new phase model or an asserted reconstruction of the unpublished code.
Reported profile enthalpy remains the actual SRK phase value. Qualify the
ideal Case 1 parity control before interpreting nonideal pilot differences.
Prefix any variant with `smooth-` to select the already tested C4 continuation
of the Soave alpha function. This is a separately named diagnostic, not Liang's
reported model. It sets both phase and transport SRK evaluations consistently.
Alternatively, prefix with `signed-` to retain the signed Soave factors in
mixture attraction. This reconstructs the polynomial mixing used in the pinned
OF6/OF8 sources; it does not identify Liang's implementation. Pure-fluid
attraction remains unchanged. Negative or zero mixture-factor sums use a
division-free fugacity expression. The prefix occupies the same position as
`smooth-`; both cannot be selected together. Frozen checks cover the EOS,
enthalpy derivatives, Gibbs identities, alpha crossings and pure-fluid parity.
See the [source audit](../../docs/liang-srk-root-sign-audit-20261021.md).
`GRID_FACTOR` is 1 (default), 2 or 4. Every interval of the initial grid is
subdivided by this factor before solving, while the same numerical guess is
interpolated onto it. This tests actual global grid refinement even when the
adaptive error criteria would otherwise retain nearly every initial node.
The original grid and final grid sizes are recorded. The grid limit rises to
12000 for this explicit refinement diagnostic.
Prefix with `midpoint-` (before optional `smooth-`) to distribute the ordinary
diffusion correction using face-averaged mass fractions, as in the inspected
PREMIX 2.5b source. Cantera 3.2 uses left-node mass fractions. This isolated
discretization control supports mixture-averaged mole-gradient diffusion with
Soret off; it does not change binary coefficients or assert Liang's exact
PREMIX release. `DiffusionFlow.h` applies it to the selected energy equation.
Compare ideal and nonideal pilots at two global grid factors before drawing
a conclusion about this numerical difference.
The build runs 32 frozen face-state checks: zero net mass flux, zero flux for
uniform composition, and antisymmetry when the two faces are exchanged. A stock
left-node control must fail the antisymmetry condition, proving that this test
distinguishes the changed stencil. These are numerical invariants, not evidence
that Liang used this particular source release.

An ideal HP equilibrium profile supplies only the initial steady-solver guess.
An optional solved CSV guess is also only a steady numerical initial guess.
No transient CFD checkpoint or restart is used. Each solve records grid
refinement, inlet speed, mass flux, outlet temperature, species and property
profiles. `transport.csv` compares ideal and real transport at identical T,p,X
along the solved flame, including H2, O2, N2 mixture and H2–N2/H2–O2 binary
diffusivity ratios. These definitions remain distinct because Figure 6 does not
identify a particular diffusivity.

## Dependencies and boundaries

The driver reuses `cantera-liang` SRK, transport, pressure-chemistry and energy
adapters and the pinned Cantera 3.2 SDK. Preparation uses Python/Cantera 3.2.
Builds and flames run through Slurm, one CPU per flame. `job.sh` confines HOME,
cache, temporary files and outputs to the project root. `submit.sh plan` is
read-only; `apply` submits an explicitly bounded build or solve. A completed
build and binary hash are required for solves. Failed jobs remain evidence.
No secrets are read or stored by the module. Site paths are command arguments.
The figure gallery consumes results; production solvers do not depend on them.

## Figure coverage and qualification

| Figure | Required calculation | Qualification limit |
| --- | --- | --- |
| 2 | H2/air and CH4/air mixture critical points | Reuse existing critical audit; Pc discrepancy remains unresolved and is independent of kinetics |
| 3 | Cases 1–5 plus 3star, phi=1–2.1 | Energy/transport implementations labelled explicitly |
| 4 | Cases 1/2, phi=0.6–3; fresh density and rho_u S_L | Unit conversion: kg/m3 /1000; kg/m2/s /10 |
| 5 | Cases 1/2/3/3star, phi=0.85–1.35 | Report flame endpoint, not substituted HP equilibrium |
| 6 | Stoichiometric transport ratios versus temperature | Show named diffusion definitions; no claim of unique paper identity |
| 7 | Stoichiometric T and H2/O2/HO2/H2O2 mole fractions | Translate x by a declared temperature marker; never stretch x |

First run phi=1 and 1.4 pilots. Require finite states, normalized species,
positive transport, convergence, and final speed change below 0.5% between the
last two grids before widening coverage. Domain-width and Tu sensitivity remain
separate checks. Grid refinement alone does not establish agreement with Liang.

## Minimal example and verification

```sh
python3 prepare.py plan /data/burke.yaml /data/species.txt /new/hydrogen-inputs
bash submit.sh plan ROOT RELEASE SDK INPUTS build - kshcnormal
bash submit.sh apply ROOT RELEASE SDK INPUTS build - kshcnormal
# After build qualification:
bash submit.sh plan ROOT RELEASE SDK INPUTS 1 BUILD kshcnormal 1.0
```

Run `python3 -B prepare.py --help`, `bash -n job.sh`, `bash -n submit.sh`,
and `git diff --check`. Build qualification runs the existing independent SRK,
alpha and Takahashi checks before compiling the hydrogen driver. Each flame
checks CP against finite differences and the partial-enthalpy Euler identity.
The chemistry-law check compares six reactive frozen states against independent
ideal-phase evaluations at physical p and p/Z. It includes third-body/falloff
terms and requires the chemistry adapter to preserve physical SRK density.
The activity check separately verifies forward/reverse mass action against
the factor `product((Z*phi_fugacity)^stoichiometry)` at fixed physical states,
and tests elemental conservation and detailed balance after VCS TP equilibrium.
No additional fugacity correction is applied to kinetic prefactors.
The ideal control must also agree with a separately solved stock Cantera flame
before treating discrepancies as nonideal model effects.
`stock_control.py plan|apply MECHANISM OUTPUT --phi 1.4` supplies that independent
Python control with the same final grid criteria and 6000-point limit.

`collect.py plan|apply JOBS_JSON SNAPSHOT --host SSH_ALIAS --root ROOT` performs
remote reads only and writes a new local snapshot plus scheduler state. Each job
row has `job`, `case`, `phi`, and `transport` (`lj` or `pairs`). Its resulting
manifest feeds `plot.py plan|apply PAPER MANIFEST CRITICAL_CSV SPECIES_TXT OUTPUT`.
New runs copy the checked executable hash, build and SDK paths, escaped command,
and numerical-guess hash into the job directory. The collector retains these
records when present; it does not invent them for historical jobs.
The renderer uses NumPy/PyMuPDF, preserves source panels at publication scale,
adds open-symbol legends, and exports six PNGs, a PDF and evidence JSON.
Original caption crops remain beneath the original panels at their publication
scale. Their measured PDF rectangles are recorded with the figure evidence;
report page height can change without resizing either scientific panel.
Out-of-range samples are counted, not forced inside the original axes.
Figure 7 uses independently fitted vector tick coordinates and translates the
computed 1500 K crossing to the paper's 0.9801270683 cm crossing. Its calibration
is recorded in the artifact. The earlier 0.00025 cm tick-spacing interpretation
was wrong by a factor of two; superseded galleries must not support width claims.
The finite paper window is distinct from the full-domain flame endpoint.
`figure2-6-calibration.json` supplies the other measured axes; Figure 6 retains
raster uncertainty. A 0.02-point frame tolerance preserves boundary points
within vector calibration precision. Missing/out-of-range intervals are never
bridged by a connecting line. Run `python -B test_plot_geometry.py`: expect
vector tick residuals below 0.02 point, raster residuals below 0.12 point, and
5 micrometres mapped to approximately 18.5079 PDF points in Figure 7.

`digitize.py plan|apply PAPER NEW_OUTPUT` extracts hash-pinned original vector
paths for Figures 3/4/5. It writes raw vertices, native marker centers, tick
calibration, uncertainty bounds and PNG verification overlays. It does not fit
to calculations or extrapolate; interpolation samples identify dash gaps.
It depends on PyMuPDF, NumPy and Matplotlib, with no runtime solver dependency
or secrets. Run `plan`, then `apply`, and inspect the overlays and tick residuals
before using extracted points for a paper-comparison screen.

`diffusion_definitions.py plan|apply INPUTS PROFILE TRANSPORT_CSV NEW_OUTPUT`
replays the independently checked Takahashi table at saved LJ flame states and
reports every named species' mixture diffusivity ratio. It first checks the H2,
O2 and N2 values against the actual C++ output. It depends on Cantera 3.2,
NumPy and `validation/diffusion`'s independent table/correlation, with no flame
solve or coefficient fit. Author-pair inputs are rejected by this LJ-only probe.
An unnamed paper diffusivity is not identified merely by a nearby computed curve.

`compare.py plan|apply MANIFEST REFERENCE_JSON NEW_OUTPUT` compares completed
baseline runs against the independently extracted Figure 3/4/5 geometry.
It reports uncompleted jobs, grid changes and profile conservation diagnostics.
Figure 3 uses the existing methane screening rule: absolute speed error no larger
than max(0.05 cm/s, 1% of reference) plus the figure-reading allowance. Other
quantities retain raw errors and reading bounds without a new acceptance rule.
The partial-temperature control is not eligible as a reconstructed paper Case 3*.
LJ and author-pair curves remain separate; duplicate points fail explicitly.
It uses NumPy and the local digitizer, with no new solver or remote writes.
Run the plan first and inspect the resulting CSV and failed-point list.

`ledger.py plan|apply MANIFEST PROJECT_ROOT NEW_JSON` creates a compact,
shareable identity ledger from an already collected snapshot. It records each
completed point, refinement change, source revision and result-file SHA256.
Snapshot references are relative to the supplied project root. Historical build
identity is explicitly a source-to-build registry association when the original
job did not record its build path; it is never represented as a directly
observed job field. New jobs instead use their collected build path, executable
hash and source record. Their declared build/source/variant must agree with
the observed files. The public ledger retains the build job number and hashes,
not machine-specific SDK or command paths. Version 2 distinguishes these two
identity bases per run and preserves diagnostic variant names.
The script uses only the Python standard library and reads
no secrets, network, scheduler or simulation state beyond its supplied snapshot.
Its output is a reviewed evidence summary, not a scientific acceptance decision.
Verify unique job IDs, complete input coverage and the recorded file hashes.
