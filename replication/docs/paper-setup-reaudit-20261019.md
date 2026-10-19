# Paper setup re-audit, 19 October 2026

The 1-D premixed cases are the smaller controlled test for solver development.
Their 4,000-cell mesh already has the paper's 0.5 micrometre spacing. They do
not reproduce the paper's ignition and boundary configuration, and the current
OH result is a saved-field estimate rather than a direct evaluation of Equation
(40). The 2-D results currently plotted still use 11,200-cell tutorial meshes;
the corrected meshes have 816,000 or 888,000 cells. A code change cannot be
judged from those two different setups without keeping their identities separate.

This is a primary-source and input audit, not a new simulation or a diagnosis
that a particular discrepancy causes the observed flame-speed error. No jobs,
solver code, or case dictionaries were changed for this audit.

## Evidence and identity

Fresh scheduler and deployed-dictionary inspection is saved locally in
`state/debug-audit-20261019/live-dictionaries-and-cost.json`. Measured costs:

| Case | Cells / allocated cores | Physical advance in this job | Wall time | Core-hours |
| --- | --- | --- | --- | --- |
| 1-D phi=1.10, 124797651 | 4,000 / 4 | 0 to 1 ms | 10:11:25 | 40.76 |
| Coarse 2-D oxyfuel 1 atm, 124767586 | 11,200 / 8 | 1 to 70 ms | 8:06:53 | 64.92 |
| Coarse 2-D oxyfuel 200 atm, 124767667 | 11,200 / 8 | 0 to 70 ms on initialized donor state | 9:33:40 | 76.49 |
| Fine 2-D 1 atm, 124805217 | 888,000 / 32 | 9 us saved after mapped warm start | 3:00:01, timeout | 96.01 |
| Fine 2-D 200 atm, 124805218 | 816,000 / 32 | 9 us saved after mapped warm start | 3:00:27, timeout | 96.24 |

The full 1-D sweep took 9:25:35–10:13:27 per condition, approximately 38–41
core-hours each. It is the cheapest paper-spacing flame for repeated diagnostic
experiments. It is not faster than the coarse counterflow in physical milliseconds
per wall hour: at the endpoint, premixed uses dt=1e-7 s (maxCo about 0.099), while
coarse counterflow uses dt=2e-5 s (maxCo about 0.157/0.137). Their flow scales,
mesh spacing and chemistry tolerances differ. Do not compare wall time per step
or domain dimension alone as an efficiency measure.

Fine cases actually specify maxCo=0.2 and maxDeltaT=1e-6 s, but their observed
late steps remain 2e-7 s at maxCo about 0.019/0.025. Their 1-us adjustable output
cadence requires an isolated time-control check before more expensive runs;
the limiting mechanism is not established by the dictionaries alone. Each late
fine step costs approximately 210–220 seconds on 32 cores. The two dependent
steady continuations did not start. None of these endpoints demonstrates the
paper's steady-profile stopping criterion.

- Nguyen et al., [2022 library paper](https://doi.org/10.1016/j.cpc.2021.108264),
  supplied PDF `1-s2.0-S0010465521003763-main.pdf`. Pages below are both printed
  and PDF page numbers. Sections 4.2 and 5.2–5.3, Table 1, Equation (40), and
  Figure 12 discussion were checked in the local full text, with pp.10–11
  extracted again directly from the PDF.
- Nguyen and Yoo, [2025 solver paper](https://doi.org/10.1016/j.cpc.2025.109600),
  supplied PDF `1-s2.0-S0010465525001031-main.pdf`; Section 2 was re-read directly
  from PDF p.2.
- Juanos and Sirignano, *Pressure effects on real-gas laminar counterflow*,
  *Combustion and Flame* 181 (2017), 54–70, local
  `state/juanos-sirignano-2017.pdf`; printed pp.56 and 60 were re-read directly
  from PDF pages 3 and 7. This is Nguyen's reference [38], case 6.
- Actual completed 1-D run metadata: `state/liang-profiles-20261019.json`,
  observed 2026-10-19 08:38:52 Asia/Shanghai. All eleven jobs, 124797642 through
  124797667 in the recorded list, contain final samples at 0.001 s. Metadata
  agrees with [premixed cases](../development/premixed-inlet/cases.json).
- Code reviewed at checkout `611eae9a476fd9dafa439a3cb29428d91700ebfd`:
  [premixed preparation](../development/premixed-inlet/prepare.py),
  [runtime finalization](../development/premixed-inlet/runtime.py),
  [equilibrium seed](../development/premixed-inlet/equilibrium.py),
  [base numerical dictionaries](../validation/flames/generate_counterflow.py),
  [counterflow reconstruction](../development/counterflow/prepare.py), and
  [flame-speed analysis](../suite/flame_speed.py).

The [18 October counterflow audit](counterflow-reference-audit-20261018.md)
contains the archived live-input checks for the coarse jobs. Statements below
about the corrected fine cases refer to their versioned generator; checkpoint
and scheduler status are separately recorded evidence, not inferred here.

## Premixed: explicit matches, adaptations, and missing specifications

| Item | 2022 paper | Completed inlet cases | Classification |
| --- | --- | --- | --- |
| Fuel, pressure, fresh temperature | CH4/air, 100 atm, 298 K (§5.3 p.11) | 10,132,500 Pa, 298 K, CH4/O2/N2 | Matches stated conditions. Air is implemented as 21/79 molar O2/N2; that ratio is our explicit convention. |
| Chemistry and property families | GRI-Mech 3.0, SRK, realFluid-JANAF, Chung–Takahashi (§5.3 p.11) | Same selected families and pinned author GRI input | Family match; does not establish identical historical species-property tables or library revision. |
| Grid | Uniform 0.5 micrometres, at least 40 points through flame (p.11) | 4,000 cells over 2 mm, hence 0.5 micrometres | Spacing matches. Actual resolved thickness must still be measured. |
| Initial condition | Fresh mixture throughout, central hot ignition, two outward combustion waves (p.11) | Left half fresh, right half ideal-gas HP equilibrium products, sharp initial interface | Deliberate topology/initialization adaptation, explicitly different. |
| Boundaries | Pressure `waveTransmissive` at both distant outlets (p.11) | Fixed T/composition/U at left inlet; left pressure zeroGradient; right pressure waveTransmissive; right T/species/U zeroGradient | Deliberate boundary adaptation, explicitly different. |
| Inlet speed | No prescribed inlet in the two-outlet configuration | Approximate Liang curve values, 0.0534–0.0701 m/s | Project input guess, never the computed flame speed. |
| Domain length | Outlets sufficiently distant that they scarcely affect flames; no numerical length stated (p.11) | 2 mm, interface initially at 1 mm | Paper-unspecified reconstruction. Boundary independence is unproved. |
| Stopping criterion | Structure and propagation speed invariant after ignition transient (p.11) | Stop at 1 ms; finite/normalized endpoint check | The published physical condition has not been demonstrated by reaching the chosen endpoint. |
| Speed definition | Density-weighted OH displacement, chemistry plus diffusion, Eq.(40) | Fixed OH crossing tracked across saved samples, local density/velocity correction | Related continuum quantity; different discrete evaluation. Temperature-front result is an additional project diagnostic. |
| Marker and averaging | OH selected, but no OH level or time window specified | Explicit thresholds and fitting windows in campaign manifest | Project analysis choices; require sensitivity checks. |

Actual run metadata uses initial flow step `1e-9 s`, `maxCo=0.1`,
`maxDeltaT=1e-7 s`, writes every `1e-5 s`, and four ranks. Do not substitute
the older generic `maxCo=0.2` / `maxDeltaT=2e-7 s` settings when describing these
jobs. The base generator uses Euler time differencing, limited-linear convection,
one outer PIMPLE corrector, two pressure correctors, and SEULEX `absTol=1e-8`,
`relTol=1e-6`, initial chemical step `1e-8 s`. The paper's inspected flame
sections do not specify these numerical values. A tolerance or coupling study
is therefore a numerical qualification, not a correction to a known paper value.

The ideal-gas seed uses the author's NASA7 coefficients and an offline Cantera
HP calculation. It does not enforce SRK equilibrium or conserve real-fluid HP
across the initial interface. Runtime finalization enforces equal initial mass
flux using the actual library's densities; it does not fix that energy/equilibrium
difference. For phi=1.10 the recorded initial densities are 112.79985 and
14.57572 kg/m3, giving product velocity 0.54250 m/s for inlet 0.0701 m/s.
These are initialization values, not a measurement of final flame equilibrium.
Evidence: `equilibrium.py:generate`, `runtime.py:finalize`, and actual job
124797651 metadata.

At a fixed rising OH isoline, the continuum species balance gives
`Sd* = (rho_f/rho_u) (u_f - dx_f/dt)` for our coordinate orientation.
The paper instead evaluates
`[omega_OH - div(rho Y_OH V_OH)] / [rho_u |grad(Y_OH)|]`.
Our finite-time trajectory fit can differ through temporal fitting, interpolation,
operator splitting, and discrete diffusion/source treatment. Instrument the actual
solver source and corrected diffusion flux to compare both at the same cells and
times. Reaction rate alone does not implement Eq.(40). The temperature-gradient
peak is not a fixed species isoline; agreement requires a settled travelling
profile. See the detailed [definition audit](flame-speed-definitions-20261018.md).

Nguyen p.13 says the Liang comparison uses Ely–Hanley viscosity/conductivity
corrections, while Nguyen uses Chung; Liang also uses modified PREMIX rather
than transient OpenFOAM. Do not tune to the Liang inlet curve as if it were
Nguyen's numerical output. Both reference series belong in the plot, with
Nguyen's symbols the primary replication target. This distinction is established
by Nguyen's full text; no additional claim about Liang's unavailable full
implementation is made here.

## Counterflow: completed coarse fields versus corrected fine inputs

Nguyen §5.2 p.10 specifies pure methane at 300 K against exact 21/79 molar
O2/CO2 at 1000 K; plug-flow inlets; strain
`2 (|UF|+|UO|)/L = 100 s^-1`; equal inlet momentum flux; total-pressure outlet
at 1 or 200 atm; zeroGradient for remaining outlet fields. Table 1 specifies:

| Condition | Paper radius × separation | Paper radial / axial spacing | Completed coarse mesh | Corrected reconstruction |
| --- | --- | --- | --- | --- |
| Oxyfuel 1 atm | 20 × 20 mm | 20 / 20–30 micrometres | 80 × 140; radial 250, central axial 133.33 micrometres | 1,000 × 888 = 888,000 cells |
| Oxyfuel 200 atm | 5 × 5 mm | 5 / 5–10 micrometres | 80 × 140; radial 62.5, central axial 33.33 micrometres | 1,000 × 816 = 816,000 cells |

The coarse baseline therefore has an explicit paper mesh mismatch even after
longer integration. It also retains rounded oxidizer O2 mass fraction 0.162,
mixed U/T outlet types, and at 1 atm tutorial velocities 0.467/0.533 m/s.
The corrected generator fixes exact molar composition, density-based momentum
matching, and zeroGradient non-pressure outlets. Uniform radial spacing and
the stated axial ranges are represented, but stretched-zone extents and grading
are reconstructed because the paper does not publish them. Fine-grid warm-start
mapping is another project choice; steady-state independence from that initial
state must be checked. Evidence: `counterflow/prepare.py:plan/main`,
[inlet finalization](../validation/flames/finalize_inlets.py), and the archived
live-input section of the 18 October audit.

For CH4/air at 100 atm, Nguyen p.11 instead adopts Juanos case 6: 20 × 20 mm
axisymmetric domain, 5-micrometre flame-zone mesh, GRI30, and matching reference
boundary conditions. Juanos pp.56/60 prescribes both inlets at 300 K, methane
speed 1 m/s, and **equal opposing mass flux**, not the oxyfuel equal-momentum
constraint. The current adaptation implements that distinction correctly.
Nguyen explicitly allows its 2-D geometry and mixture-averaged diffusion to
differ from Juanos's 1-D similarity and multicomponent diffusion. Those are
declared differences in the paper itself, not discrepancies to eliminate.

The air mesh's radial interpretation is less explicit than oxyfuel Table 1;
our 7,912,000-cell fine draft is a reconstruction, not an exact published count.
The tutorial-derived air case retains CO2 as closure species after changing
the oxidizer to O2/N2. The paper does not identify its closure species. N2
closure is a useful controlled sensitivity with species/element balances, not
a proven correction. The failed full air case and its short smoke profile
cannot support a steady Figure 11 comparison.

## Boundaries for code changes and first discriminating experiments

The 2022 model includes mixture-averaged species diffusion, mixture molecular
weight/correction terms, species enthalpy diffusion, chemical source terms, and
no Soret/Dufour/radiation (§4.2 pp.8–9). The 2025 paper explicitly omits chemical
reactions and uses unity Schmidt/Lewis assumptions (§2 p.2). Its modified
PIMPLE loop is a possible isolated numerical-development idea, not a replacement
physical model for the 2022 reacting validation. Our OF8 library is also later
than the publication-era OF6 implementation; see the source-linked
[solver](solver-paper-audit-20261017.md) and
[thermophysical](thermo-architecture-audit-20261017.md) audits.

Recommended controlled order, with no jobs submitted by this audit:

1. Keep phi=1.10 as the small diagnostic case. First establish late-time profile,
   fixed-OH-level, time-window, and element/energy balance stability. Compare
   direct Eq.(40), kinematic OH, and a complete fuel-consumption balance; the
   latter two definitions are not extra methods claimed by Nguyen.
2. Compare the current inlet topology with a separately versioned central-hot-
   ignition/two-outlet case at identical chemistry, transport, spacing and
   numerical controls. Declare the unspecified ignition width/temperature and
   test sensitivity. A paired longer domain tests the boundary-distance claim.
3. Use one-variable time-step, chemical-tolerance, and coupling changes before
   interpreting a solver/library patch. Run property inversion regression for
   any thermo change; inspect changes in balanced terms rather than just the
   final Figure 12 point. Do not choose an estimator for proximity to a target.
4. For 2-D, separate outlet/composition/inlet corrections on the coarse baseline
   from mesh changes. Use intermediate meshes to estimate position and profile
   sensitivity before expensive final paper-resolution qualification. Final
   acceptance still requires the published spacings and steady profiles.

Domain independence, a stable travelling wave or steady counterflow, and numerical
refinement are tests of the replication. Neither 1 ms nor 70 ms is a stopping
time specified by the 2022 paper.
