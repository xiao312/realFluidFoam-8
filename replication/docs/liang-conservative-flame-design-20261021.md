# Conservative species and total-enthalpy free-flame control

21 October 2026, Asia/Shanghai. Design audit only; no implementation or jobs.

A common-face control can retain Cantera 3.2's free-flame continuity,
temperature anchor, inlet and outlet. Changing only interior species advection
is structurally compatible with those equations at a converged positive mass
flow. Keep **all stock interior species rows** in the first diagnostic; no
dependent-species replacement is required without evidence of a conditioning
problem. The optional alternative below replaces, rather than adds, one row.
This is a numerical conservation experiment, not an established explanation
of Liang's flame-speed discrepancy.

This note specifies details missing from the
[earlier control review](liang-conservative-control-review-20261021.md).
The [profile audit](liang-energy-conservation-audit-20261021.md) remains the
quantitative evidence: grid refinement changes speed by about 0.1%, versus a
several-percent paper gap, and removing elemental drift lowers the already-low
rich product temperature. Those observations do not justify selecting this
discretization by its agreement with the paper.

## Residuals and scope

Let `m_j=rho_j*u_j`, `dx_j=z_(j+1)-z_j`, and
`w_j=(dx_(j-1)+dx_j)/2`. For face `f=j+1/2`, define

```text
m_f = (m_j + m_(j+1))/2
up(f) = j if m_f >= 0, otherwise j+1
G_k,f = m_f*Y_k,up(f) + J_k,f
F_f = m_f*h_up(f) - lambda_f*(T_(j+1)-T_j)/dx_j
      + sum_k(J_k,f*hbar_k,f)
```

`G` has units kg/(m2 s), `F` W/m2, `hbar` J/kg, and
`W_k*wdot_k` kg/(m3 s). Use the native face `m_flux(k,j)` as `J`, including
its correction velocity; do not reconstruct a second diffusion flux inside
the residual. Use mixture total enthalpy and partial species enthalpies, with
the existing molar-to-mass conversion. The first control should retain its
declared no-Soret, no-radiation, adiabatic, constant-pressure free-flame setup,
without two-point control or a simultaneous thermodynamic-model change.
The energy flux is already implemented by
[`TotalEnthalpyFlow`](../development/cantera-liang/TotalEnthalpyFlow.h).

For interior physical species rows and enabled energy rows, use

```text
R_k = [W_k*wdot_k - (G_k,right-G_k,left)/w_j]/rho_j
      - rdt*(Y_k,j-Y_k,j,previous)
R_T = -(F_right-F_left)/(w_j*rho_j*Cp_j)
      - rdt*(T_j-T_j,previous)
```

Their units are 1/s and K/s. Keep `diag=1` for these relaxation rows. The
smallest implementation calls stock `evalSpecies` and changes each interior
physical row by

```text
delta R_k = [m_j*dYdz_k - div(m_f*Y_k,up)]/rho_j.
```

This preserves native chemistry, diffusion and pseudo-time terms. The stock
diffusion denominator already equals `w_j`. It also preserves boundary work
performed by the base method. The parent total-H class retains fixed-temperature
rows during initialization. No separate chemical heat-release source belongs
in this total-enthalpy equation.
[Pinned species and energy residuals](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L700),
[native diffusion](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L477)

## Species normalization and the dependent row

Stock Cantera solves **all** species equations at interior nodes. It replaces
only one row at each boundary with normalization; the boundary excess species
can differ at the two ends. Keeping all interior physical rows is therefore
the literal minimal override, and is not automatically overdetermined. Their
sum supplies a transport equation for `S=sum(Y)`, with normalized boundary
data. Nevertheless, its conditioning is a separate issue from conservation.
[Actual row selection](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L786)

Only if an explicitly constrained follow-up is justified, select a fixed, present
dependent species by name, for example N2, at construction. At every interior
node replace its row by `R_dep=1-S`, with `diag=0` and no pseudo-time term.
N2 need not be chemically inert for this derivation. Do not select the largest
species anew at each interior node or Newton iteration, and do not silently
normalize the solution vector or alter the phase's `NoNorm` setters. Retain
the existing boundary excess-species choices and connector equations.

At normalized states, mass-conserving chemistry and zero summed diffusion,
the sum of the **physical** species residuals is

```text
sum_k(R_k,physical) = -div(m_f)/rho_j - rdt*(S_j-S_j,previous).
```

Consequently the dependent physical equation follows from the other rows
only when continuity is satisfied and the previous pseudo-time state is
normalized. At steady state `rdt=0`. Reconstruct and report its physical
residual rather than reporting the algebraic normalization row as evidence of
species conservation. This reconstruction is mandatory for that optional
replacement, not an extra equation for the all-species control. Validate
normalization before beginning pseudo-time;
do not hide an inconsistent previous state with post-solve projection.

One relevant off-manifold detail is explicit in the source: ordinary mixture
diffusion uses left-node raw `Y` in its correction. If `Q_f=sum(J_raw)`, then
`sum(J_f)=Q_f*(1-S_left)`, not identically zero for an unnormalized Newton
iterate. For positive flow the all-species formulation gives
`sum(G_f)=m_f+(m_f-Q_f)*(S_left-1)`. Thus a small `m_f-Q_f` can weaken its
normalization equation. This is an algebraic observation, not a measured
failure of current flames. An explicit dependent row avoids relying on this
transport equation for normalization, while retaining the native flux API.
[Flux correction](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L491),
[unnormalized state setters](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L289)

## Continuity, boundaries and pseudo-time

The free-flame continuity rows constrain every adjacent pair of nodal mass
flows. Their direction changes around the temperature anchor; the anchor's
velocity row fixes temperature, but the neighboring rows still connect both
sides. Thus all `m_j`, and hence all averaged `m_f`, are equal at convergence.
Off convergence `div(m_f)` is generally nonzero: this is a coupled continuity
residual, not an additional source to subtract from species advection.
Subtracting `Y*div(m_f)` would defeat the stated conservative control.
[Continuity and anchor](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L568)

At the inlet the connector sets `m_0*Y_k,0+J_k,1/2=m_0*Y_k,feed` for
independent boundary species. Positive flow selects `Y_0` for first-face
advection, so this equals `G_k,1/2` when `m_1=m_0`. At the outlet, zero species
and temperature gradients supply the matching last-face state. Keep both
boundary normalization equations. The normal inlet/outlet pair is explicitly
left-to-right: reverse-flow **interior stencil tests** are useful, but a
negative converged mass flow is not an admissible reversed-boundary flame.
Boundary agreement depends on continuity tolerance and must be measured.
[Inlet](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Boundary1D.cpp#L200),
[outlet](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Boundary1D.cpp#L424)

These are steady residuals with diagonal relaxation in `Y` and `T`, not a
conservative physical transient discretization of `rho*Y` and `rho*h`.
Cantera constructs the steady Jacobian, then subtracts `rdt*diag` from its
diagonal. Replacing relaxation by finite differences of `rho*Y` or `h` while
keeping this mask introduces unrepresented cross-variable derivatives.
Preserve the stated scaling and positive finite `rho,Cp` checks. Do not add
new density or composition time derivatives to this bounded experiment.
[Jacobian evaluation](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/OneDim.cpp#L286),
[transient diagonal](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/MultiJac.cpp#L48)

## Verification required before a flame interpretation

- **Frozen stencils:** with constant mass flow and uniform spacing, compare
  every independent physical species row with stock `TotalEnthalpyFlow` to
  roundoff, for positive and negative flow. Test nonuniform spacing separately;
  exact parity there is neither expected nor desirable. If a later control
  replaces one row, compare its reconstructed physical residual separately.
- **Independent balance identity:** for arbitrary test fluxes, verify
  `sum_j(w_j*rho_j*R_k)=sum_j(w_j*W_k*wdot_k)-Delta G_k`
  at `rdt=0`. At finite `rdt`, include
  `-rdt*sum_j(w_j*rho_j*Delta Y_k)`. Likewise check
  `sum_j(w_j*rho_j*Cp_j*R_T)=-Delta F-rdt*sum_j(w_j*rho_j*Cp_j*Delta T)`.
  Use separately assembled flux arrays, both signs, unequal spacing and
  nonconstant trial mass flow. Include every species balance.
- **Jacobian and masks:** compare local perturbation evaluations with full
  evaluations under the same frozen-transport policy, including points next
  to boundaries and the anchor. Verify `J(rdt)-J(0)=-rdt*diag`; all interior
  species masks stay one in the first control. The stencil remains within
  three neighboring nodes.
- **Solved conservation:** record `sum(Y)-1`, minimum species fraction,
  adjacent nodal mass-flow differences, `sum(J)`, mass and elemental chemical
  source sums, all-species physical residuals, and elemental face fluxes
  `sum_k(n_e,k*W_e/W_k)*G_k,f`. Compare measured boundary differences with
  integrated residuals, without cancellation-sensitive relative scaling.
- **Boundary/domain and mesh:** check feed-to-first-face flux and flat end
  states. The telescoping identity covers interior dual volumes; it does not
  add reactions in omitted boundary half-cells. Repeat ideal and nonideal
  controls on globally refined grids with identical physical models. Report
  speed, product temperature, elemental and full enthalpy flux convergence.
  Finite-grid agreement with stock temperature energy is not a parity test.

`Flow1D::eval` refreshes nodal thermo before energy and species, including
Jacobian-local calls; transport coefficients are intentionally frozen during
ordinary Jacobian perturbations. Build face advection from the current vector
and refreshed densities. Do not reuse a previous-call face cache or query
rates from the phase state left behind by the energy loop. Use cached native
`wdot`, `J`, `lambda` consistently. Retain the present nearest-neighbor
dependency and connector evaluation order.
[Property update](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L358),
[bulk-before-connector evaluation](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/OneDim.cpp#L254)

Conservation alone does not establish accuracy. First-order upwind face values
still require refinement, particularly across abrupt grid-spacing changes.
Both normalization choices have the same intended normalized steady equations;
the explicit dependent row changes nonlinear conditioning and needs its own
checks. A passing control establishes this numerical property, not Liang's
unpublished PREMIX discretization or a corrected physical model.

Inspected integration source: `851e6115a4aeb531ab356b9b034f6340a0f42a9e`.
Cantera `Flow1D.cpp` SHA-256:
`c6b16e3dcc46c05738386501cd1fdf3d143c7b0cb7f858f570a291d037b56b79`;
project `TotalEnthalpyFlow.h`:
`9d33f621a0d43b5b20c47716377f71ff57ee5a9656c226101e2cadbbb192a151`.
The pinned local Cantera source was inspected directly. The public source
link was accessible; the documentation-site requests timed out. No new
source download or numerical flame result is claimed.

## Implementation qualification added after the design review

The named `conservative` control now implements the all-species construction.
The separate `total-enthalpy` option retains stock species equations while
forcing total H in ideal Case 1, allowing the two changes to be distinguished.
The original default remains unchanged. Native node/source/residual and
face/enthalpy-flux outputs are available only for the conservative control.

Isolated Slurm job `125095225` compiled the actual flow header and exercised
sixteen residual fixtures, with uniform/unequal grids, both flow signs,
constant/varying mass flow and zero/nonzero pseudo-time rate. It passed:

| Check | Maximum error |
|---|---:|
| Weighted global species telescoping balance | 1.11e-16 |
| Stock equivalence on a uniform grid at constant mass flow | 1.73e-17 |
| Summed species residual versus continuity | 4.30e-16 |
| Partial versus full residual range | 0 |
| Perturbed residual nearest-neighbor locality | 0 |

The nonuniform fixture differs from the stock stencil by up to 0.05304 in
residual units. Boundary rows and diagonal masks are checked directly.
This establishes the discrete residual behavior, not a completed flame
qualification. The committed build reruns the fixture before any pilot is
eligible; physical conservation and grid checks remain required afterward.
