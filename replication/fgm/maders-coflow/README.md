# Maders 2017 reacting coflow preparation

`profile_flow_audit.py` reads retained radial profiles, the hash-bound three-patch
mass-flux collection, and a bounded native `energyState` log excerpt. It reports
axial/radial velocities, axisymmetric advective mixture-fraction flux, and the
final Euler global mass balance. It does not modify a case, fit chemistry, infer
missing diffusive flux, or establish stationarity. Radial quadrature excludes
unsampled end caps; its full-annulus approximation is separate from the exact
wedge patch balance. Inputs are explicit local paths; output is a new directory,
with source hashes and scientificAcceptance=false. NumPy and Python standard
library only; no scheduler, network or secrets. Default mode is a read-only plan;
use `--apply` to write. Example: `python profile_flow_audit.py --samples TIME_DIR
--flux-collection COLLECTION.json --mass-log EXCERPT.txt --out NEW_DIR --apply`.
Verify against the retained A07 final-step mass/flux values and reject mismatched
patch hashes or a final-time mismatch. The caller must bind the log excerpt to
the actual job and executing source; an excerpt alone is not a full-log receipt.

`timestep-co0125.json` declares an original-zero temporal-refinement control:
same A07 physical table, geometry, inlets and50ms upper-progress ignition,
maxCo0.125/maxdt25us instead of0.25/50us, requested end250ms. Apply its values
through the existing `prepare_case.mjs` read-only plan before case generation.
The batch binds the exact JSON hash. Compare matched times and profile drift;
neither peak agreement nor synthetic tests establish temporal convergence.
The coarse Co1 control and every failed/unsteady profile remain evidence.
Dependencies, secret handling and scheduler ownership are unchanged.

`startup-earlier-ignition.json` declares a separate original-zero coarse-grid
startup experiment. It retains paper inlet profiles, composition, absolute Ha,
physical table and source integration, but ignites at0.05s rather than0.9s and
uses maxCo1 rather than0.5. It tests initialization memory and available post-
ignition settling time; it is not a paper ignition protocol or a convergence
certificate. Pass these declared values to the existing `prepare_case.mjs`;
its dry-run plan must precede case creation. No scheduler, network or new
dependencies. Verify emitted control/manifest values and actual ignition/time
receipts; compare matched post-ignition ages and finite-window drift before
interpreting paper agreement. No restart or continued evolved state is permitted.

Prepare physical flamelets and explicit case inputs for Maders Figures 4–6.
This module does not submit jobs, fit paper curves or establish CFD validation.

Inputs: the retained DeepFlame DRM19 YAML (21 species, 84 reactions), versioned
case contract and a new output directory. Outputs: actual steady flamelet profiles,
raw species/source arrays, residuals, table-coordinate diagnostics and provenance.
The flamelets use Spitfire mixture-fraction equations with prescribed Peters scalar
dissipation, ideal-gas chemistry, adiabatic unity-Le transport, variable Cp and
enthalpy flux. They are table building blocks, not radial coflow profiles.

Dependencies: pinned Spitfire/Griffon, Cantera 3.2, NumPy, SciPy in an allocated
Linux environment. The future developed OF8 solver consumes the exported data.
No network, credentials, scheduler or arbitrary code execution is exposed here.

`hybrid_lookup.py` compares a declared linear or PCHIP source interpolation
against retained physical held-out states. Temperature and species use the
unchanged baseline. It accepts data only, never candidate Python code.
Run it with `--assets TASK_DIRECTORY --scheme linear --out NEW_DIRECTORY`.
The input directory contains `training/manifest.json` and `evaluation/*.npz`.
Its metrics establish a hybrid-connection diagnostic, not new flamelet convergence
or coflow agreement. The retained training family includes a reported failed
high-dissipation solve; this limitation remains in every result.

Example: `python flamelets.py --config case.json --out NEW_DIR --plan`.
Remove `--plan` within FlamePilot-admitted Slurm compute. Every flamelet uses a
fresh equilibrium numerical guess. No evolved CFD state is imported.
Verification: exact mechanism/source hashes; chemical rate interface; finite raw
profiles; mass/element/enthalpy errors; measured RHS residual and grid sensitivity.
A converged flamelet is not a comparison with the two-dimensional paper target.

## Source audit

Maders PDF pp.2–5 defines 298 K atmospheric methane/air, diluted fuel 55/45,
weighted progress gamma=sum(Yi/MWi), i=CO2,H2O,H2; bilinear lookup; Smooke transport.
Verhoeven 2011 thesis PDF p.44 (printed37) establishes volume fractions, 12 mm
fuel diameter, 27.5 mm outer radius, 0.1 m height, parabolic fuel Umax=0.23 m/s,
uniform air0.23m/s, outer no-slip and zero-gradient outlet except pressure.
Maders incorrectly calls the 12/55mm dimensions radii and prints an inconsistent
parabolic formula. Use the thesis geometry and standard axial parabolic profile
U(r)=Umax*(1-(r/Rfuel)^2); record this reconstruction, not exact author case files.
The thesis uses300K; default298K follows Maders, with a300K sensitivity planned.
One atmosphere=101325Pa and dry air O2:N2=1:3.76 are declared reconstructions.
Source reference: https://pure.tue.nl/ws/portalfiles/portal/3577661/719415.pdf
Maders: https://www.abcm.org.br/proceedings/view/COB17/0722

Gamma units are kmol/kg when MW is kg/kmol. Its volumetric source is kmol/m3/s.
Our planned CFD coordinate C=MW_H2O*gamma is dimensionless; its volumetric source
is kg/m3/s. A weighted-reader extension is required; the existing unweighted sum
must not silently be used. Signed sources remain signed. The table chemistry and
Smooke transport must not be replaced by Chung/SRK for the atmospheric replication.

Famou task preparation is separate. The owner deferred actual Famou execution;
no cloud assignment is launched by this module.

`mesh.mjs --out NEW_DIR --plan` describes the reconstructed axisymmetric40000-cell
wedge. Remove `--plan` to write a fresh mesh case. Node built-ins only; no solver
execution or credentials. Actual `blockMesh`/`checkMesh` run in FlamePilot Slurm.
The inlet lip is zero-thickness and the structured mesh differs from the author's
unavailable unstructured100000-cell mesh. These are explicit diagnostic choices.
`reader_states.py` exports nine actual DRM19 cold/half-composition/equilibrium nodes;
`reader_probe.C` checks the real OF8 reader against them. They are parity controls,
not a physical flamelet table and never the table for a production coflow run.

`lookup_baseline.py` consumes only declared training profiles and query coordinates.
It performs mapped weighted-C piecewise-linear interpolation with explicit coverage
refusal. `evaluate_lookup.py` reads separate fixed held-out physical references and
predictions. It reports T/species/signed-source errors, coverage, weighted-C and mass
consistency without declaring scientific acceptance. These tools are the portable
Famou task contract; no external task is launched by running them. NumPy only.

`export_table.py` builds a v3 table from five declared physical profiles, explicit
cold mixtures and HP-equilibrium limits. Chi5/10 remain held out. Sparse progress
gaps are linear reconstructions, not additional solved flamelets. It verifies
finite composition and weighted C, writes NASA7 metadata and fresh seed inputs.
It depends on the existing direct-flamelet metadata exporter and NumPy/Cantera.
`prepare_case.mjs` consumes exact table/metadata hashes and creates a new coflow
case only. It reuses the existing NASA exporter and solver schemes. No submission,
credentials or evolved CFD import occurs. Its dry-run is `--table DIR --plan`.
The first case uses an analytical cold fuel column plus a hot ring at timezero,
40000cells, upwind convection, Smooke transport and stock buoyancy force/energy.
It is a startup diagnostic; comparison with steady paper data needs a stable time
history and mesh/scheme checks. NASA coefficients are unchanged; bounds extend to
290K for slight flow-induced cooling near298K. This extrapolation is declared.

After actual blockMesh, `apply_inlet.mjs CASE --plan` computes each actual fuel
face centroid and parabolic velocity. `--apply` replaces only the fresh inlet
placeholder with fixed values, retaining mesh hashes and measured flow quadrature.
It refuses evolved cases or an unexpected patch. It reuses the existing G2 ASCII
mesh parser; no dynamic boundary compilation or model fitting occurs.

`initialize_Ha.C` reuses the existing guarded runtime-initialization pattern with
stock-compatible types. On the actual fresh mesh, it constructs the selected
Smooke thermo, computes Ha from its own h/Hf and prescribedT/Y, verifies actual
mu/kappa dispatch, and writes the required time-zero/thermo-type marker. It does
not read evolved fields or change p/T/Y. The remaining inversion audit remains
unchanged. Use before decomposition and after setFields, within the admitted job.

Warm OF8 build packets must include the standalone fgmDimixPolicy.H dependency
used by the retained steadyFlamelet module, even when its optional real-fluid
optimization is disabled. Add that exact source directory to CPATH; do not edit
or copy files into the stock read-only OpenFOAM installation. Runtime Ha
initialization is performed after setFields and before decomposition. Its marker
binds actual selected thermoType at timezero, leaving the solver guard enabled.

The case retains conservative density and explicit mixture-fraction/energy audits.
Historical strict lookup, 64epsilon-only projections and1e-14 scalar solves are
recorded in [12 November progress](PROGRESS-20261112.md); they are not the current
operational protocol. Per-stage correction accounting refers to weighted progress
mass, not loss of total mixture mass. Outer iterations are separate evaluations;
do not sum them as independent physical time steps.

The selected case requests two thermo correction passes at unchanged internal h.
thermo_switch_probe.C exercises actual selected OF8 N2 thermodynamics across
1000 K, reproduces the stock single-pass residual and checks refinement without
writing any fields. The caloric closure limit stays1e-8. Physical coflow agreement
and the exact previous failure remain separate from this probe.

13November operational rerun: boundsPolicy clamp replaces the roundoff-only
source guard. Source input projection and held endpoint events are measured,
not silently accepted as physical accuracy. Strict diagnostic APIs remain usable.
The case uses practical equation tolerances: pressure1e-7/relative0.01 with
final relative0 and200iterations; Z/C1e-10; velocity/energy1e-9. Histories expose
remaining conservation, temporal and profile defects. This is a new numerical
protocol, not a retrospective pass for the old run.

The generated case writes radial profiles and inlet/outlet mass flux every5ms.
Full fields are less frequent. `convergence.mjs` reads these actual saved profiles
and writes a provisional steady-screen receipt. Its plan mode makes no writes.
The declared screen starts after two nominal domain traversals (0.87s), compares
both planes over50/100ms lags, and requires three consecutive50ms-spaced checks
with max temperature change10K and max CO change5e-4. This is a practical
time-settling screen, not a paper-agreement gate or a formal validation claim.
All earlier and failed profiles remain available. If it does not settle, report
the transient/oscillatory history rather than selecting a favourable frame.
The [operational rerun record](../../docs/maders-operational-rerun-20261113.md)
binds the actual compiled source, checks, resources and interpretation limits.

Boundary audit amendment,13November: Maders Fig.1 specifies free-slip at the
outer boundary, whereas the thesis specifies no-slip. The executed case uses
no-slip and is therefore not an exact Maders boundary match. See
[case audit](../../docs/maders-case-audit-20261113.md) for the measured inlet,
mesh/scheme, startup and manifold differences and proposed discriminating checks.

## Paper-aligned protocol (13 November development)

The optional `--protocol paper` case preparation selects the Maders free-slip
outer wall, zero-gradient velocity outlet, limited second-order spatial convection
and a120000-cell structured wedge with60micrometre radial spacing over r6–12mm.
Axial spacing remains200micrometres: this is improved resolution, not an exact
copy of the unavailable unstructured mesh or a grid-convergence claim. The baseline
protocol stays reproducible. `--protocol paper-fine` prepares a400080-cell mesh
with approximately60micrometre axial spacing for a later sensitivity.

Paper protocol begins with cold air everywhere and cold inlet composition/enthalpy.
A default-off solver ignition schedule evolves cold flow with chemistry suppressed
until0.9s, then sets progress to the local table-source peak near stoichiometric Z
within4mm of the exit. This occurs before time advancement in the same process;
no saved/evolved CFD field is imported. Fifty-millisecond Z/U changes are reported
throughout cold flow; the scheduled time is not a claim of cold-flow convergence.
Absolute enthalpy is retained, composition/thermo are refreshed and the density/
energy jump is logged. Pressure/enthalpy ownership is unchanged. The reacting
settling monitor starts its clock at ignition. Verify actual compiled execution,
cold source suppression, one ignition event and time-zero provenance in Slurm.

`quenching.py` computes a separate denser physical Spitfire flamelet family and
transient extinction snapshots, using the retained mechanism/software environment.
It writes source/species/enthalpy/residual diagnostics and a manifest; it never
approves, exports to CFD automatically, or replaces an existing table. Inputs are
case.json and the mechanism, outputs a new directory. No network/secrets. Plan:
`python quenching.py --config case.json --out NEW_DIR --plan`. Run actual integration
only inside a FlamePilot-admitted Slurm allocation. Compare coverage and held-out
source errors before table integration; Peters-chi remains a declared approximation.

Verhoeven2011, printed page49/PDFpage56, explicitly extends its non-premixed
steady flamelet family with time-dependent quenching states beyond extinction.
Our quenching extension follows that construction choice; it is not a reason
to replace the physical family with steady profiles alone. Remaining differences
include prescribed Peters scalar dissipation versus resolved counterflow strain,
finite trajectory sampling and mapped progress coordinates. Strain rate `a` and
stoichiometric scalar dissipation `chi_st` both have units1/s but are not equal.
The reference's uniform201x201 tabulation also differs from retaining the
clustered physical flamelet Z grid. Source:
https://pure.tue.nl/ws/portalfiles/portal/3577661/719415.pdf#page=56

`export_table.py --mixture-fraction-grid uniform` isolates that Z-grid choice.
It resamples the same hash-bound physical family on201uniform Z points, keeping
the existing mapped progress interpolation, source values, cold/equilibrium
limits and chemistry. The default `profile` retains the previous numeric path.
The plan and receipt state the selected grid. This numerical control is not a
new solved flamelet family or an exact replica of the author's absolute-progress
grid. Qualify default numeric-table parity (excluding only the source-header
revision), candidate mass/progress consistency, actual reader parity and the
unchanged held-out data before an independently fresh CFD comparison. Neither
held-out scores nor a new grid imply scientific acceptance. No new dependencies,
network or secret access; all actual construction/CFD uses admitted Slurm compute.

`qualify_export_grid.py` checks that control before CFD. Inputs are the retained
baseline, a default-path re-export and a uniform-Z export. It requires numeric
default-table parity (only the declared source header may differ), unchanged
NASA/species/stream properties, exact uniform coordinates and finite conserved
mass/progress/element-derived mixture fraction. It records all consumed hashes.
It does not replace the independent C++ reader or held-out evaluator. Example:
`python qualify_export_grid.py --baseline BASE --reproduced DEFAULT --candidate
UNIFORM --out NEW_DIR`; add `--apply` only after the read-only plan. NumPy and
standard library only, no network/secrets. Qualification failures preserve the
input/output directories and stop that candidate's CFD phase; no chemistry or
scientific comparison criteria are adjusted to make it pass.

`export_table.py --family-manifest MANIFEST` accepts only hash-bound finite
transient quenching snapshots and residual-qualified steady members, withholding
chi5/10 from training. It preserves all failures in provenance, writes a201x201
mapped table when the physical Z grid has201points, and retains the old explicit
cold/equilibrium boundary construction. Without this option the baseline export
is unchanged. `evaluate_export.py` queries the exported numeric table against the
same frozen held-out reference used for the baseline; it never changes reference
coordinates or predictions to improve the metric. NumPy only; no credentials or
scheduler. Example: `python evaluate_export.py --table TABLE/table.npz --reference
REFERENCE.npz --out NEW_DIR`. Verification: same reference hash, coverage, finite
species/source and weighted-C consistency; C++ lookup/runtime checks stay separate.

## Source/ignition debugging controls

The default outer velocity boundary is `noSlip`, matching Verhoeven2011 PDFp44.
An audit on16November found that the former `paper` protocol silently selected
`slip`; actual retainedR19/0/U confirmed it. That executed result remains unchanged
and must carry the mismatch. `--outer-wall-velocity slip` explicitly reproduces
that historical diagnostic; the selected boundary enters the case manifest.
No-slip is a setup correction, not an established explanation for profile error.
Compare matched fresh-zero cases before attributing improvement to this change.

`field_audit.py` independently reconstructs table temperature/source from the
exact executed NPZ at sampled Z/raw-C, and compares transported Ha with the
linear inlet enthalpy. Inputs are that NPZ, its expected SHA256, initialization
JSON and one radial sampling directory. It reads only, or writes a new JSON
receipt with `--out`; `--plan` reports paths/hashes without calculations. Requires
NumPy, no Cantera, network, scheduler or secrets. This does not replace CFD or
acceptance: point interpolation differs from cellwise closure, heat diffusion
and mechanical work can produce nonzero enthalpy differences, and out-of-table
samples are counted rather than silently extrapolated. It flags stale sampled
diagnostic fields separately. Verify on retained physical samples, then reject
a deliberately wrong table hash. Example:

Optional `--metadata PHASE.json --pressure-pa 101325` additionally reconstructs
ideal-gas nodal density from the exported T/Y, then applies mapped interpolation.
It compares that field with sampled rho. This diagnoses the distinction between
interpolated table density and EOS reconstruction in Maders; it is not SRK and
must not be used as a G2 real-fluid density evaluator. Metadata order/hash and
the reference pressure are recorded. It does not reconstruct the author's table.

```sh
python field_audit.py --table TABLE.npz --table-sha256 SHA256 \
  --initialization initialization.json --samples radialProfiles/TIME --plan
```

`closure_probe.py` compares the actual two exported tables at fixed Z/C with
Cantera DRM19 chemical sources evaluated at both tabulated T and the existing
inlet-mixed absolute enthalpy. It invokes `source_replay_probe.C`, linked to the
actual OF8 reader/source integrator, and compares fixed-density table-source
replays with independent adiabatic constant-pressure Cantera reactor histories.
The density treatments differ and are explicitly labeled; this is a source/ignition
diagnostic, not coflow or paper validation. Tables, mechanism and executable hashes
are retained. No fitting, coefficient changes or reference changes occur.
Inputs: two physical table directories, mechanism, compiled probe, new output dir.
Outputs: source rows, chemical reactor/replay histories and provenance JSON.
Dependencies: retained Cantera3.2/NumPy environment and the existing compiled OF8
reader. No network/secrets. Plan: `python closure_probe.py --baseline OLD_TABLE
--candidate NEW_TABLE --mechanism drm19.yaml --probe BIN --out NEW_DIR --plan`.
Execute chemistry/compilation only inside admitted Slurm compute; verify finite
states, unchanged enthalpy and exact actual-reader replay receipts. Failed physical
behavior must remain visible, not converted into a passed paper comparison.

Case preparation exposes `--ignition-mode sourcePeak|upperProgress`,
`--ignition-z-min/--ignition-z-max`, `--max-co`, `--max-delta-t` and
`--mesh-protocol baseline|paper|paper-fine` for separately declared sensitivities.
Defaults reproduce the previous protocol. Record every setting in the case plan;
short10ms-cold-flow cases are fast extinction controls, not paper comparisons.
Hold the table, mechanism, enthalpy coupling and other settings fixed while varying
one ignition or timestep setting. Use the actual solver logs/profile histories to
judge post-ignition survival, and then requalify successful changes in the full case.

`--ignition-step-reset yes|no` and `--ignition-delta-t SECONDS` bind the numerical
ignition reset explicitly in generated dictionaries and case receipts. Defaults
yes/1e-6s reproduce the corrected event. Long cases must qualify a short fresh
startup first. The numerical reset does not make a too-small kernel physically
viable; matched controls must keep that distinction visible. Case purpose and
short/long cold-flow durations remain explicit in operator records.

Full-case sampling includes Ha, tabulated diagnostic temperature, progress source
and diagnostic heat release alongside the comparison fields. Separate axial
profiles at r1/4/6/8/10mm help distinguish an anchored flame from an advecting hot
ignition kernel. This changes diagnostic output only. Raw fields stay on SCNet;
retrieve only the selected profiles/metrics for local comparisons.

`--axial-cells INTEGER` permits a separately declared axial-resolution diagnostic
without changing the radial mesh, geometry, physics or initialization. The default
still follows the selected mesh protocol. For paper geometry,1000 axial cells give
100micrometre spacing and240000 total cells. This remains coarser than the cited
30–60micrometre guidance and is not an exact author mesh. Record the actual mesh
receipt/checkMesh result; a plan alone is not executed-grid qualification.
Example: `node prepare_case.mjs --table TABLE --protocol paper --axial-cells 1000
--ignition-time .9 --end-time 2 --ranks 32 --plan`. Verify default and override plans,
reject nonintegral counts,then run actual blockMesh/checkMesh through Slurm. Compare
matched physical times with the coarse case before attributing profile differences
to resolution. Every refined CFD starts at its original timezero.

`timestep-co00625.json` declares a third original-zero temporal control after
`maxCo=.25/.125`: `maxCo=.0625`, maximum timestep12.5microseconds, unchanged
250ms horizon, mesh, table and50ms ignition. It is configuration for the existing
case interface, not a new model. Plan with the declared values, verify its hash
against the batch control and compare profiles at matched physical times with
the earlier levels. Smaller timestep alone does not establish convergence or
turn a transient snapshot into a steady paper result.
