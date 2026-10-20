# Review of a common conservative species and enthalpy control

2026-10-21, Asia/Shanghai. Source inspection only; no implementation or jobs.

Do not prioritize another flame experiment on this hypothesis to explain the
remaining Liang hydrogen speed discrepancy. Existing refinement and flux
measurements make it a weak explanation. A common conservative discretization
remains useful for numerical qualification, but its benefit should be measured
as conservation and convergence, without selecting it by agreement with Liang.
This narrows the earlier [energy audit's proposed next check](liang-energy-conservation-audit-20261021.md).

## What the existing evidence establishes

The original-alpha Case 3 total-enthalpy runs have energy-flux spans below
0.019 K equivalent and flat inlet/outlet diffusion fluxes. Their measurable
elemental drift comes from the different advection and diffusion denominators
in stock Cantera's nonuniform-grid species equations.

At phi=1.4, the existing C4 partial-temperature refinement controls give:

| Job | Points | H-element change, % | Speed, cm/s | Product T, K |
|---|---:|---:|---:|---:|
| `125071518` | 1824 | −0.19729 | 75.52361 | 2300.87770 |
| `125071524` | 3631 | −0.09919 | 75.44738 | 2300.08472 |
| `125071526` | 7258 | −0.04836 | 75.46081 | 2299.91284 |

The full speed range is 0.07623 cm/s, or 0.101%, while Liang Case 3 is
approximately 71.81 ± 0.33 cm/s. The existing matched-enthalpy controls also
track the partial-temperature result closely. Removing the elemental drift
would lower the rich product temperature by roughly 1.8 K, worsening its
comparison with the already higher paper temperature.

This is not a rigorous upper bound on every discretization error. The
finest partial-temperature run retains a 0.317 K energy endpoint defect;
the speed sequence is not monotone, and a completed factor-four
matched-enthalpy profile is not present in the inspected snapshot. We therefore
cannot claim a formal asymptotic limit. Nevertheless, the available effect is
far smaller than the persistent 2–8% Case 3 speed discrepancy and has the wrong
temperature direction. See the [nineteen-profile audit](liang-energy-conservation-audit-20261021.md)
for profile hashes, reconstructed fluxes and endpoint-equilibrium calculations.

## Smallest well-defined future control

For an interior node j, let
\(w_j=(\Delta x_{j-1}+\Delta x_j)/2\). On face f between nodes j and j+1, use
the existing total-enthalpy class's mass flux and upwind node:

\[
m_f=\tfrac12[(\rho u)_j+(\rho u)_{j+1}],\qquad
G_{k,f}=m_fY_{k,\mathrm{up}}+J_{k,f}.
\]

Retain its energy flux unchanged:

\[
F_{h,f}=m_fh_{\mathrm{up}}
 -\lambda_f(T_{j+1}-T_j)/\Delta x_j
 +\sum_kJ_{k,f}\bar h_{k,f}.
\]

Use \((G_{k,j+1/2}-G_{k,j-1/2})/w_j=W_k\dot\omega_{k,j}\) for every
interior species and the existing zero-divergence energy equation for total h.
This shares face mass flow, upwinding and control-volume width between species
and energy. It keeps the physical diffusion, chemistry and thermodynamic
partial-enthalpy definitions fixed.

The minimal code boundary would be a named subclass of `TotalEnthalpyFlow`
overriding only `evalSpecies`: first call the stock method, then replace its
interior convective term \(m_j\,dY_k/dx\) by the face convective divergence.
Leave reaction rates, diffusion, pseudo-time terms and boundary equations as
the base method computed them. The existing `EnthalpyFlow` in `EnergyFlows.h`
is a different control: it makes energy use stock species advection and does
not make either species advection conservative on a nonuniform grid.
[Project total-H implementation](../development/cantera-liang/TotalEnthalpyFlow.h),
[matched-stencil implementation](../development/liang-hydrogen/EnergyFlows.h),
[pinned species residual](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L786)

The stock free-flame continuity equations and temperature anchor can remain.
They enforce constant mass flow at a converged steady solution. The inlet
condition uses nodal mass flow, while the proposed first face uses its average
with the next node; equality therefore relies on satisfying continuity and
must be checked. The outlet imposes zero temperature/species gradients.
Preserve the boundary excess-species normalization constraint.
[Continuity](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L568),
[inlet](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Boundary1D.cpp#L200),
[outlet](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Boundary1D.cpp#L424)

No new derivative stencil extends beyond j−1, j, j+1. `Flow1D::eval` updates
properties before energy and species, including partial Jacobian evaluations.
Compute face advection from the current x and refreshed nodal densities;
do not reuse a face cache from an earlier residual evaluation. Keep the SDK's
transport-update policy and cached diffusive fluxes unchanged for this control.
The existing temperature pseudo-time term is a steady-solver aid, not a claim
to integrate a conservative transient total-energy equation.
[Evaluation/update sequence](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L358)

## Qualification before interpreting a new result

There is no machine-precision ideal-flame parity requirement for this change:
even ideal chemistry now solves a different discrete species system on a
nonuniform grid. The appropriate checks are:

- At constant mass flow on a uniform grid, frozen species convective residuals
  equal the stock upstream formula to roundoff. Check both velocity signs.
- On nonuniform grids, the width-weighted sum of conservative divergences
  telescopes exactly to the boundary-face difference. Verify it independently
  for each species and for total h, including partial Jacobian calls.
- With \(A_{ek}=n_{ek}W_e/W_k\), check both
  \(\sum_k A_{ek}W_k\dot\omega_k=0\) and constant elemental face flux
  \(\sum_kA_{ek}G_{k,f}\). Check \(\sum_kJ_{k,f}=0\), \(\sum_kY_k=1\),
  and constant mass flow separately. Compare residual-weighted integrated
  imbalances with the measured boundary differences, rather than assuming a
  small nonlinear solver norm proves conservation.
- Compare ideal and nonideal versions on actual globally refined grids with
  identical inputs, smooth alpha, chemistry law, transport, boundary placement
  and solve tolerances. Record speed, product temperature, elemental fluxes and
  full enthalpy flux. Require convergence toward the corresponding stock-grid
  limit; do not use exact equality at one finite grid as the acceptance test.

The primary stock discretization is documented as upstream advection with
centered diffusion. Conservation of the proposed control does not establish
that it was used in Liang's unpublished PREMIX implementation, and does not
make a first-order upwind flame grid-independent.
[Cantera 3.2 discretization](https://cantera.org/3.2/reference/onedim/discretization.html)

Source reviewed: integration commit
`c9c2c55b3db6b9b6f379026ad94ff4fdea17d34c`.
Pinned Cantera `Flow1D.cpp` SHA-256:
`c6b16e3dcc46c05738386501cd1fdf3d143c7b0cb7f858f570a291d037b56b79`.
Project `TotalEnthalpyFlow.h` / `EnergyFlows.h` SHA-256:
`9d33f621a0d43b5b20c47716377f71ff57ee5a9656c226101e2cadbbb192a151` /
`2935dbe3ff7f750936ff1315e75c4a2581625b0f58bb30bb00f8dfb2de58fdaf`.
