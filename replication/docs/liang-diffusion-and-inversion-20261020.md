# Liang Case 5 diffusion and CFD energy qualification

20 October 2026, completed-reference-wave update. Case 5 remains outside the digitized-paper screen
on the rich side. The tested diffusion alternatives do not explain the missing
Case 4-to-5 reduction. A separate, demonstrated temperature-inversion error is
fixed and has passed the existing native-library checks. Two short ideal CFD
diagnostics finished from newly generated zero-time fields. One matched-transport
control is submitted as 125041726. No new 2-D
campaign is active.

## Case 5 findings

At phi=1.40, digitized Liang gives Case 4 = 5.795719 and Case 5 = 5.642738 cm/s,
a reduction of 0.152981 cm/s. The current calculation gives 5.807094 and
5.762399 cm/s, a reduction of only 0.044695 cm/s.

| Test at phi=1.40 | Case 4 (cm/s) | Case 5 (cm/s) | Case 4-to-5 reduction (cm/s) |
|---|---:|---:|---:|
| Digitized paper | 5.795719 | 5.642738 | 0.152981 |
| Current baseline | 5.807094 | 5.762399 | 0.044695 |
| Mass-fraction-gradient formulation | 5.777965 | 5.733245 | 0.044720 |
| Whole-mixture critical averaging | — | 5.781626 | — |
| Additional mesh refinement | 5.799594 | 5.754848 | 0.044747 |

Mass-gradient Case 5 remains high by 0.090507 cm/s, or 1.60%; whole-mixture
critical averaging remains high by 0.138888 cm/s, or 2.46%. Neither passes the
declared paper screen at this condition. Changing the gradient basis shifts
Cases 4 and 5 almost equally. The whole-mixture alternative worsens Case 5.
Neither alternative replaces a baseline curve merely because one point is closer.

The frozen-state probe independently reconstructed the mixture coefficient
`D_i=(1-Y_i)/sum(j!=i, X_j/D_ij)` from the binary matrix. It checked 53 species,
eight flame states, and both pair and bulk critical-property rules: 848 checks.
Maximum relative error was 7.7716e-16, binary asymmetry was zero, and maximum
relative net diffusive mass flux was 2.3371e-16. This rules out that conversion
as the discrepancy's cause. It does not establish the author's transport inputs.

| Diagnostic | Job | Final mesh points | Last refinement change |
|---|---|---:|---:|
| Frozen diffusion audit | 125029670 | Not a flame solve | Not applicable |
| Ideal mass-gradient control | 125029569 | 2263 | 0.1254% |
| Case 4 mass-gradient | 125029619 | 2204 | 0.1685% |
| Case 5 mass-gradient | 125029635 | 2198 | 0.1556% |
| Case 5 whole-mixture critical averaging | 125029652 | 2195 | 0.1561% |
| Case 4 additional refinement | 125027407 | 4021 | 0.1292% |
| Case 5 additional refinement | 125027408 | 4024 | 0.1310% |
| Same Case 5, converged steady numerical guess | 125033536 | 4022 | 0.1370% |

All completed flames in this table pass the existing numerical screen. The
diagnostic source is `116bb7ecd04b524d0c3befc2a769892af4d2d77c`, build 125027773,
with Cantera SDK 124917358. The additional-refinement jobs use source 97d9ce9
and build 124951950, except the independent-guess job, which uses 116bb7e/125027773.
They retain the original alpha and energy formulation; only a third refinement
level is added. Fine Case 5 remains 1.99% above the digitized paper. Independent
steady guesses differ by 0.000249 cm/s, or 0.00433%. These checks do not establish
asymptotic grid convergence, but their changes are much smaller than the paper gap.
Job 125033536 independently starts the steady solve from the completed Case 5
profile's 2196-point grid to avoid repeating its earlier difficult iterations.
This is a Cantera numerical guess; no transient CFD state is continued.

Source d4c115d adds a frozen nonideal-driving-force probe, built as 125037886
and run as 125039385. At each face it evaluates composition derivatives of SRK
log fugacity at the same midpoint T and p, avoiding an accidental Soret term.
The additional corrected flux has an L1 magnitude of 2.12% of baseline near
401 K, 1.07% near 600 K, 0.215% near 1200 K, and 0.0133% near 1800 K.
These are local flux ratios, not flame-speed errors. The 848 previous coefficient
and mass-flux checks remain unchanged and pass. A constant-TP Gibbs–Duhem test
also passes. No flame equation uses this additional term. Giovangigli et al.
(2011), Section 4.2, describes the chemical-potential driving force, but does not
establish that Liang used it with Takahashi coefficients. The main Liang article
specifies binary correction and mixture averaging without its detailed flux equation.

The corrected Takahashi Table 2 coefficient remains in use. Species critical
parameters and the precise binary-mixture reduction used by Liang remain
unpublished inputs. The dense-conductivity increment is also a named model
interpretation. Agreement of Cases 1–4 therefore does not establish complete
implementation identity. No coefficient has been fitted to the flame-speed curve.

## Native temperature inversion

The previous draft passed 288 small-increment checks but failed one of 450
property states: SRK, 50 atm, 190 K. It recovered 189.99964594841 K. Independent
bisection of the original 50–4000 K bracket with a 1e-3 K stopping width gives
that exact value. The fallback's coarse resolution caused this remaining failure.

Source `ef60c736b5ce802f3918980dc895a944bd1bbadb` changes the fallback width to
1e-6 K. It retains the earlier correction that returns the final Newton update
and uses a 1e-9 relative Newton step tolerance. The physical models, bracket and
test limits are unchanged.

| Qualification | Job | Result |
|---|---|---|
| Full library build | 125030062 | Completed in 20 min 4 s |
| SRK/PR small increments | 125030399 | 288/288 passed |
| SRK/PR property sweep and inversion | 125030427 | 450/450 passed |

The full source archive was verified against all 1,647 Git blobs before upload.
Use `git -c core.autocrlf=false archive`; Windows line-ending conversion previously
invalidated a build archive. Build and numerical qualification are distinct from
flame-speed agreement.

## Short CFD diagnostics

The new `cantera-wave` module maps screened ideal Cantera profile 124920014 to
two opposed fronts. Their half-temperature contours start at 1.9 and 2.1 mm in
the existing 4-mm, 8000-cell domain. Both cases have identical T and all 53 Y
fields; one starts at U=0, and one uses the reference's travelling-wave velocity.
On the right this is `u_b-u_ref`, mirrored with opposite sign on the left.
Here `u_b` is the reference velocity at the joined centre state. The independently
calculated reference speed relative to fresh gas is 7.461703 cm/s. Imposed initial
velocity is not counted as a measured CFD flame-speed result.

| Fresh diagnostic | Job | Case source | Library build |
|---|---|---|---|
| Profile T/Y, zero initial U | 125035576 | 5f946723070f100e062852202021c5aeef5ae4c7 | 125030062 |
| Same T/Y, travelling-wave U | 125035588 | 5f946723070f100e062852202021c5aeef5ae4c7 | 125030062 |
| Travelling U, Cantera kappa/Dimix | 125041726 | 6bf3cb8a7f550aa316a4f4bcfb27474857c85210 | 125030062 |

These eight-rank jobs have a 20-microsecond endpoint and a one-hour wall limit
each. They retain native chemistry and transport, current-state species sensible
enthalpies, and strict linear-solver tolerances. The initial profile hash is
`09408212459b4f4b318de2310714cba6b4429d169cfad386d84c2c47962d550e`.
It must match the frozen, screened Case 1 result before case creation.
Both native jobs passed 144/144 ideal-mixture increment checks, distinct CPU
assignment, original-zero history, and finite-field endpoint checks. Their final
time is 19.994734 microseconds. This time endpoint is a diagnostic checkpoint.

| Native initialization | T-front speed (cm/s) | OH-front speed (cm/s) | Peak T (K) |
|---|---:|---:|---:|
| Zero U | 7.410815 | 6.857385 | 2229.989057 |
| Travelling U | 7.397968 | 6.857405 | 2229.583992 |

The same reference speed is 7.461703 cm/s. T remains transient, and OH disagrees
with T. Initial velocity alone therefore does not remove the mismatch. The
integrated signed Qdot across both fronts at the endpoint is 41.7563 and
41.7253 MW/m2, respectively; peaks are 2.27141e12 and 2.26934e12 W/m3.
Small negative Qdot values are retained rather than clipped. Both histories and
saved-field checks are in `liang-reference-wave-20261020.json`.

Job 125041726 changes only conductivity and mixture diffusivities through
qualified bridge 124942015. Native chemistry, thermodynamics, inversion,
strict linear solves, mesh and generated original fields are retained. The bridge
and reference ideal mechanisms must match byte-for-byte. The previous fresh-state
audit found native conductivity 6.55% above Cantera, making this a measured lead.

Job 125043700 is the native 5-ns step control, source
`499fa91439248acc5787810b88abdd1873e29ae3`. It targets the same 20-microsecond
checkpoint from identical original fields. Its eight-hour limit reserves at most
64 core-hours. Both Euler time error and chemistry averaging change with the
step, so the comparison cannot attribute a speed change to chemistry alone.
Local verification confirmed exact zero-field parity and rejected a
control/manifest step mismatch. No saved positive-time field is used.

## Integration decision

The demonstrated temperature-inversion corrections and original-zero diagnostic
modules are merged into `develop/reacting` at
`ea7211e281e3018e9aeca20a99beace2a39a28e5`; the remote branch was verified.
Risk is low within the tested scope: 288/288 SRK/PR increments, 450/450 property
inversions, both 144/144 ideal gates and both finite 20-microsecond CFD endpoints
passed. The original-zero policy, module Python/shell syntax and environment
lock also passed locally after integration. Scientific acceptance remains false.

The combined Cantera bridge additionally passed qualification 125043949.
Its ABI0 client checked 51 states in each ideal, smooth-SRK and bounded-diffusion
context, then repeated with the OF8 core library loaded. Maximum scaled property
error was 3.165e-10; relative mass-source imbalance was below 4.334e-16.
The bridge now rejects flow-only and unqualified bulk-critical options instead
of silently ignoring them. This qualification does not replace the old pinned
bridge binary used by running transport job 125041726.

Qualified new bridge SHA256:
`7f196b847665d4ffb944c7248e8d32d3bebd55cd616fc45a24df330f21bd6d20`.
Client SHA256:
`08fed502b298a4ed2db4977ea040f27e69427ea475f716a33159ad5b8e937503`.

All original-zero fields are generated anew. No CFD checkpoint, positive-time
directory, or latestTime selection is accepted. Local verification passed
normalization at 2.22e-16, exact T/Y parity between the two recipes, symmetry,
and antisymmetric U. Wrong profile hashes, pressure, unscreened references,
positive-time directories and latestTime controls were rejected.

Initial launch attempts 125031691/125031693 were cancelled and excluded. OF8
bashrc treats existing positional file arguments as additional shell settings;
it attempted to source the CSV/JSON inputs. The replacement launcher saves its
arguments in named variables and clears positional arguments before bashrc.
Jobs 125032262/125032289 then spent their allocation evaluating the full flame
mesh for a probe whose verdict only used cell 0. They were cancelled before
integration. Source 5f94672 instead generates a separate one-cell probe with
the same cell-0 composition and all 144 test combinations. Original CFD fields
were verified unchanged before the replacements were launched.

The native energy equation also uses an inert-species diffusion closure where
the species equations use a mass correction across species. The prior frozen
ideal-profile audit found a maximum sensible-energy flux difference of 10.8 kW/m2
against 13.0 MW/m2 peak conduction, about 0.083%. This is a separate candidate
for consistency improvement; it is not demonstrated to cause the current speed
error. The new initialization tests first check whether the qualified solver
preserves the known flame structure.

## Chemistry integration and source averaging

The existing eight-state probe 124897206 showed close SEULEX/CVODE parity for
the same concentration/Cp-temperature ODE. That test does not show whether an
ODE-averaged source preserves a steady reaction-diffusion profile. The new
read-only `solver-comparison/source_averaging.py` compares each frozen CVODE
interval with its own instantaneous source. It reuses the matched-reference-
pressure experiment, with no new chemistry calculation or changed flame model.

| Local ODE interval | Maximum source-vector L1 change across eight states |
|---|---:|
| 1 ns | 0.627% |
| 5 ns | 1.976% |
| 50 ns | 4.690% |
| 500 ns | 21.275% |

At approximately 1501 K, a 50-ns average changes OH from -425.178 to
-122.847 kg/(m3 s). At approximately 1962 K, OH changes sign, from -795.388 to
+846.264 kg/(m3 s). These are net sources, so cancellation can make relative
species changes large. They do not imply an integrator defect or quantify the
resulting CFD speed error. The experiment's overridden thermo reference pressure
is 100000 Pa; the source profile and mechanism hashes remain in the record.

After the transport control, the next controlled comparison reduces the CFD
chemistry/transport step with the same original fields. The prediction is reduced
early profile distortion and T/OH disagreement if source averaging is important.
A clean matched-source/transport comparison must precede any conclusion about
energy-equation or SEULEX errors. `liang-source-averaging-20261020.json` records
all four intervals, signed selected-species rates and input identities.

## Figure and record updates

`liang-figure8a-diffusion-diagnostics-20261020.json` freezes the six completed
diagnostic points with job, model flags, source, profile hash and numerical checks.
It identifies the unchanged 65-point baseline by SHA256. Pass it to
`development/cantera-liang/figure_gallery.py` with `--diagnostics` alongside the
five existing inputs documented in `liang-seven-figures-20261020.md`.

The gallery retains two overview plots and one plot per Case 1–5. Diagnostics
appear only in their respective case as unconnected squares with legends.
The paper panel remains 204 by 175 points; its original title and panel label
are copied back at their original size and position. Every panel retains the
original crop and caption beside the comparison. The existing CFD curves still
use the 13:05 capture; new diagnostic jobs are not presented as completed data.

The Lark record is updated in the existing
[Liang Figure 8(a) section](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnSSnHgwGcFEVThXv7DJEXNf).
The Case 5 discrepancy remains open. Refinement and independent guesses did not
close it. Traceable transport inputs and nonideal driving-force sensitivity remain
separate leads. CFD transport, source averaging and energy balance are separate
checks. No staged nonideal CFD or 2-D result is claimed here.
