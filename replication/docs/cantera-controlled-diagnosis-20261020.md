# Cantera model controls, 20 October 2026

Two model choices explain much of the current Liang Figure 8(a) discrepancy:
replacing the dilute conductivity model, and using SRK rather than pressure-based
ideal concentrations in reaction sources. These are diagnostic findings, not
evidence of Liang's unpublished implementation. No production OpenFOAM physics
or original-zero transient run was changed.

## Completed comparisons

All values below are at phi=1.10, Tu=298 K, author GRI30. The two-level numerical
screen requires less than 0.3% last-refinement speed change, mass-flux variation
below 0.1%, species sums within 1e-7 and no Y below -1e-9. Passing it does not
establish domain independence or publication agreement.

| 100-atm calculation | Earlier control, cm/s | Diagnostic, cm/s | Diagnostic job |
| --- | ---: | ---: | --- |
| Case 2, SRK density | 7.364797 | 7.478855, pressure-based chemistry | 124934195 |
| Case 3, SRK calorics | 6.950709 | 7.059937, pressure-based chemistry | 124934198 |
| Case 4, conductivity | 7.978760, full Ely–Hanley | 7.023334, dilute baseline plus dense increment | 124932554 |

Liang's corresponding plotted values are approximately 7.47, 7.08 and 7.12 cm/s;
these are visual estimates, not author numerical data. The conductivity pilot
uses physical-concentration chemistry. The two chemistry pilots retain baseline
conductivity. Combining those changes requires separate runs.

At 1 atm, completed Cases 1/2/3 give 37.299231 / 37.284674 / 37.261995 cm/s.
Full-conductivity Cases 4 and 5 both give 41.074385 cm/s, about 10.12% above the
ideal control. This violates the paper's reported near-coincidence at 1 atm.
The dilute-model replacement is therefore problematic independently of the
100-atm target. Dense-increment conductivity and bounded-dense Case 5 both give
37.279791 cm/s at 1 atm, within 0.053% of ideal. All seven low-pressure pilots
passed numerical screening, restoring the expected near-coincidence for the
dense-increment variants.

The full-conductivity/bounded-diffusion 100-atm Case 5 completed in 6 min 50 s
and passed at 7.869949 cm/s. It remains far above Liang: bounding diffusion alone
does not remove the conductivity mismatch. The original unbounded pilots were
still running after roughly three hours without a completed refinement.

The independent Python 3.2.0 ideal 1-atm guess was solved from scratch on the
local workstation (initial width 0.03 m, phi=1.10). Its 675-point speed was
37.505055 cm/s; the C++ control subsequently refined it to 2365 points and
37.299231 cm/s. The earlier coarse guess is not reported as the final control.

## Frozen-state and energy checks

Build 124933885 and probe 124934018 used source
`c315a326bdbea73f72f387a91ca22123a0a0dfcd`. Both sampled the saved ideal and
SRK-caloric flame profiles at 1 and 100 atm. Pressure-chemistry net sources
matched an independent ideal phase exactly at every sampled state; SRK density
was unchanged. The adapter delegates the entire net-source evaluation, including
third bodies and falloff. Overriding only activities would not perform this test.

The bounded Takahashi diagnostic restricts pair reduced temperature to [1,5]
and retains Cantera's pressure interpolation and coefficients. In-range pair
factors matched the original implementation within 1e-12. At the 399.277 K
SRK-profile state, OH diffusion changes from 6.34364e-22 to 5.39476e-7 m2/s;
the uncorrected baseline is 5.28346e-7 m2/s. This removes a numerical collapse
caused by out-of-range extrapolation; it does not validate the bounded value
or the pair pseudocritical mixing against Liang.

The energy probe reconstructs
`F = rho*u*h + sum(J_k*hbar_k/W_k) - lambda*dT/dx` with Flow1D's midpoint
transport, molar gradients and left-node mass correction. Range(F), normalized
by peak absolute conductive flux, is 0.03254% for Case 1, 0.02973% for Case 2,
0.21832% for Case 3, 0.21014% for full Case 4 and 0.19905% for dense-increment
Case 4. This is a continuous-flux diagnostic, not the exact discrete residual.
Finer ideal and Case 3 grids are required before attributing the difference to
an energy-equation defect. Endpoint enthalpy alone is insufficient.

## Runs and traceability

The machine-readable companion records the current job states and screened
results. The authoritative remote ledger is
`results/cantera-diagnostics-20261020.tsv` beneath the project trial root.
The initial eleven pilots use source c315a32/build 124933885. The combined-model
and fine-grid pilots use source 82efc52/build 124934625. The SDK remains job
124917358, pinned Cantera 3.2.0. Each job records source revision, model options,
pressure and SHA-256 input receipts. The published source branch is
`xiao312/realFluidFoam-8:develop/reacting`.

| Check | Jobs |
| --- | --- |
| Pressure chemistry, Cases 2 and 3 | 124934195, 124934198 |
| Bounded diffusion with full / dense-increment conductivity | 124934199, 124934200 |
| 1-atm Cases 1–3 | 124934201, 124934202, 124934203 |
| 1-atm full / dense-increment conductivity | 124934207, 124934208 |
| 1-atm full / bounded-dense diffusion | 124934210, 124934211 |
| Combined chemistry plus dense conductivity / bounded diffusion | 124934680, 124934681 |
| Extra grid refinement, ideal / Case 3 | 124934682, 124934683 |
| Energy audit after both fine jobs succeed | 124934721 |

Each of the fifteen flame pilots requests one core for at most four hours:
60 core-hours maximum, excluding prior controls and short build/probe jobs.
No automatic flame extension or full-phi diagnostic sweep is enabled. The energy
audit requests one core for ten minutes with afterok dependencies on both fine
jobs. Failed screening prevents that audit from reporting a qualified result.
Original Case 5 controls 124919950, 124920962 and 124922397 remain retained.

The fine-grid cases use labelled converged steady numerical guesses and add a
third refinement (slope=0.001875, curve=0.003125), retaining the 6000-point cap.
They are Cantera steady solves, not restarts of an OpenFOAM transient.

Reproduction: `submit.sh plan|apply ROOT RELEASE SDK INPUTS CASE BUILD 1.10
OPTIONS ATM`; options and pressure are listed in the companion record. The
read-only collector is `collect_diagnostics.py ROOT LEDGER.tsv CHECK_SCRIPT`.
Frozen probes and energy probes use the CLI interfaces in the module README.

## Figures and next decision

All 48 original Case 1–4 sweep points completed and passed numerical screening.
The figure keeps the paper's 204-by-175-point frame, crop and caption. Separate
square markers identify diagnostic points; they do not replace default curves.
Phi=1.44 remains in the data and outside the printed plotting range. Lark images
and the PDF attachment are replaced in the existing comparison section.

Do not expand the diagnostic phi sweep until the combined 100-atm pilots,
low-pressure limit and finer-grid energy comparison are assessed. Even improved
speed agreement leaves the unknown critical-species table, Tu assumption and
Liang's undocumented chemistry/transport coupling unresolved. No coefficient
has been fitted to the target curve.
