# Liang Case 5 diffusion and CFD energy qualification

20 October 2026, 17:30 CST. Case 5 remains outside the digitized-paper screen
on the rich side. The tested diffusion alternatives do not explain the missing
Case 4-to-5 reduction. A separate, demonstrated temperature-inversion error is
fixed and has passed the existing native-library checks. Two short ideal CFD
diagnostics are running from newly generated zero-time fields. No new 2-D
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
| Additional mesh refinement | 5.799594 | Running | Pending |

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
| Case 5 additional refinement | 125027408 | Running | Pending |
| Same Case 5, converged steady numerical guess | 125033536 | Running | Pending |

All completed flames in this table pass the existing numerical screen. The
diagnostic source is `116bb7ecd04b524d0c3befc2a769892af4d2d77c`, build 125027773,
with Cantera SDK 124917358. The additional-refinement jobs use source 97d9ce9
and build 124951950. They retain the original alpha and energy formulation;
only a third refinement level is added. The completed first two levels reproduce
the existing baseline. A running refinement is not a converged result.
Job 125033536 independently starts the steady solve from the completed Case 5
profile's 2196-point grid to avoid repeating its earlier difficult iterations.
This is a Cantera numerical guess; no transient CFD state is continued.

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
| Profile T/Y, zero initial U | 125032262 | 4a0933835db4655c8a0f692ddacdad6dac3cb9c2 | 125030062 |
| Same T/Y, travelling-wave U | 125032289 | 4a0933835db4655c8a0f692ddacdad6dac3cb9c2 | 125030062 |

These eight-rank jobs have a 20-microsecond endpoint and a one-hour wall limit
each. They retain native chemistry and transport, current-state species sensible
enthalpies, and strict linear-solver tolerances. The initial profile hash is
`09408212459b4f4b318de2310714cba6b4429d169cfad386d84c2c47962d550e`.
It must match the frozen, screened Case 1 result before case creation.
At this update both jobs are still evaluating their ideal-mixture increment
gate before CFD time integration. A running scheduler job does not imply that
the flame has advanced.

All original-zero fields are generated anew. No CFD checkpoint, positive-time
directory, or latestTime selection is accepted. Local verification passed
normalization at 2.22e-16, exact T/Y parity between the two recipes, symmetry,
and antisymmetric U. Wrong profile hashes, pressure, unscreened references,
positive-time directories and latestTime controls were rejected.

Initial launch attempts 125031691/125031693 were cancelled and excluded. OF8
bashrc treats existing positional file arguments as additional shell settings;
it attempted to source the CSV/JSON inputs. The replacement launcher saves its
arguments in named variables and clears positional arguments before bashrc.

The native energy equation also uses an inert-species diffusion closure where
the species equations use a mass correction across species. The prior frozen
ideal-profile audit found a maximum sensible-energy flux difference of 10.8 kW/m2
against 13.0 MW/m2 peak conduction, about 0.083%. This is a separate candidate
for consistency improvement; it is not demonstrated to cause the current speed
error. The new initialization tests first check whether the qualified solver
preserves the known flame structure.

## Figure and record updates

`liang-figure8a-diffusion-diagnostics-20261020.json` freezes the five completed
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
The Case 5 discrepancy remains open. Next checks are the pending refinement and
traceable transport inputs, followed by measured CFD front evolution and energy
balance. No staged nonideal CFD or 2-D result is claimed here.
