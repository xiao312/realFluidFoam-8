# Maders 2017 reacting coflow preparation

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
