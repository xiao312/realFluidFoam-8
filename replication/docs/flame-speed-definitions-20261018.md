# Flame-speed definitions for the premixed campaign

Reviewed 18 October 2026 (Asia/Shanghai). Status: source review completed;
agreement between the estimators below has not yet been demonstrated for our runs.

An interim cross-check on the 21:02 saved snapshot now illustrates that limit:
the adapted temperature-gradient method gives 6.55/6.39 cm/s for job 124780751
and 6.97/6.85 cm/s for 124780755 using 50/100-us fits. The OH estimates are
6.33/6.31 and 6.33/6.32 cm/s on those same windows. These methods do not yet
agree to a declared acceptance tolerance. Temperature-peak movement remains
sensitive to evolving profile shape and sampling; a cause is not established.
Do not select whichever estimate is closest to a paper point. Code:
`validation/figures/temperature_speed.py`; input snapshot SHA256
`eedbf8296f1d339f877516708e32d91ff8a9ca6eaa62c321d4ff6eb99f6d8cc7`.

Nguyen 2022 uses **one stated flame-speed estimator**, the density-weighted
displacement speed of an OH isoline, in Section 5.3, Equation (40). Tracking
that isoline through saved fields is a kinematic way to evaluate the same
continuum quantity. A fuel-consumption integral is a useful independent check,
but Section 5.3 does not describe it as a second method used for Figure 12.
DeepFlame provides a temperature-front tracking utility with important fixed
assumptions. Cantera `FreeFlame` instead solves a stationary boundary-value
problem whose inlet mass flux is part of the solution.

## Nguyen 2022: the quantity to compare with Figure 12

The supplied [Nguyen paper](https://doi.org/10.1016/j.cpc.2021.108264),
Section 5.3, pp. 11 and 13, gives

\[
S_d^* = \frac{\omega_k-\nabla\cdot(\rho Y_k\mathbf V_k)}
                    {\rho_u |\nabla Y_k|}.
\]

Here `omega_k` is the net **mass** production rate, `rho Y_k V_k` is the
diffusive species mass flux, and `rho_u` is the unburned-mixture density.
The numerator contains chemistry **and diffusion**. Using only reaction rate
would not reproduce Equation (40). For Cantera output, molar production rates
must be multiplied by species molecular weights before forming this expression.

The paper chooses OH as the marker. It reports that suitable marker species
and isoline levels give similar values once the flame has relaxed. It does not
give an OH mass-fraction threshold, sampling interval, or averaging-window
length. Those choices must therefore be recorded as our postprocessing choices.
The flame speed is assessed after the ignition transient, when structure and
propagation speed stop changing appreciably.

The published configuration has a central ignition region producing two
outward-moving fronts, 0.5 micrometre cells, nonreflecting pressure conditions at
both distant ends, GRI-Mech 3.0, 100 atm, and 298 K fresh methane/air. Our inlet
and half-products setup is a separate way of obtaining the same planar burning
velocity; it is not the exact published initial/boundary configuration.

### Equivalent kinematic form and sign convention

The following equivalence is a derivation from the species transport equation,
not a second estimator claimed by the paper. Define the normal into fresh gas
on the rising OH flank as `n = -grad(Y_OH)/|grad(Y_OH)|`. If the isoline moves
with laboratory velocity `v_f`, then

\[
S_d = (\mathbf v_f-\mathbf u_f)\cdot\mathbf n,
\qquad S_d^* = (\rho_f/\rho_u)S_d.
\]

For our coordinate choice, fresh gas on the left and burned gas on the right,
the rising OH flank has `n_x = -1` and

\[
S_d^* = \frac{\rho_f}{\rho_u}
        \left(u_f-\frac{dx_f}{dt}\right).
\]

Interpolate both local velocity and density at the same tracked OH crossing.
Use a fixed **absolute** OH threshold within each time fit. Defining the
threshold as a changing fraction of the instantaneous OH peak tracks a changing
level, for which the simple isoline formula acquires an additional term.
The OH peak itself has zero gradient and is unsuitable for Equation (40).
The descending burned-side crossing has the opposite gradient orientation and
must not be silently substituted for the fresh-side crossing.

Saved-field tracking and direct source/diffusion evaluation can disagree because
of temporal fitting, interpolation, discretization, and source splitting. Label
the former an **OH kinematic estimate of the paper's displacement speed**, not
a direct evaluation of Equation (40). A direct evaluation should use the solver's
actual species diffusion/source implementation, including its corrections.

## DeepFlame: temperature-front motion relative to the inlet

Reviewed source pin:
`deepmodeling/deepflame-dev@7cb3294b275525cb8829ada3d3fbc067ab9323eb`.
The [utility source, lines 31–73](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/applications/utilities/flameSpeed/flameSpeed.C#L31-L73)
locates the cell with maximum positive `dT/dx`, then reports initial first-cell
`U_x` minus the change in front position divided by **0.001 seconds**. It reads
velocity from time `0`, starts from a hardcoded position of **0.0211 m**, uses
cell-centre positions, and applies no local density factor.
Its formula is therefore

\[
S_{L,T} = U_{x,0,\mathrm{first\ cell}}-\Delta x_{\max(dT/dx)}/0.001.
\]

The [documentation](https://deepflame.deepmodeling.com/en/stable/utility.html#flame-speed)
describes the subtraction in the opposite order; the executable source controls
this audit. The utility is called by the pinned
[flame-speed test](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/test/Tu500K-Phi1/Allrun#L12-L14),
so this is implemented postprocessing, not only a tutorial setup convention.

For our runs, adapt the concept as `S_L,T = u_u - dx_T/dt`, using actual saved
times and measured fresh-gas velocity. Do not copy the hardcoded utility
unchanged. In a relaxed one-dimensional travelling wave, continuity gives
`rho_f (u_f - v_f) = rho_u (u_u - v_f)`, so this upstream-relative estimate
and the local density-weighted displacement estimate should agree. This
equivalence requires a steady shape in the moving frame; early compressible
transients, changing upstream state, and moving marker definitions can break it.
Use subcell peak interpolation or a sufficiently long fitted window to control
cell-centre stair-stepping in the temperature-marker estimate.

## Cantera: a solved inlet speed in the stationary flame frame

Cantera's [one-dimensional governing-equation documentation](https://cantera.org/3.2/reference/onedim/governing-equations.html#inlet-boundary)
states that the freely propagating flame's mass flow rate is not prescribed:
an interior fixed-temperature condition anchors the flame and determines that
rate. The resulting unburned inlet velocity is

\[
S_L = \dot m''/\rho_u = u(0).
\]

The official [freely propagating flame example](https://www.cantera.org/stable/examples/cxx/flamespeed.html)
reads the first solved velocity as flame speed, after the nonlinear solve.
An initial velocity estimate helps initialize the solver; it is not the final
measured speed. Conversely, prescribing an inlet velocity in our transient
OpenFOAM case does not solve a flame-speed eigenvalue: the front may drift,
and its motion must be included in the speed estimate.

The quantity has the same physical meaning for a relaxed, unstrained planar
flame, but matching that definition does not match the constitutive models.
A standard `gri30.yaml` Cantera flame uses its configured ideal-gas thermodynamics
and transport, not automatically Nguyen's SRK/realFluid-JANAF/Chung–Takahashi
combination. Cantera 3.2 documents nonideal flame capabilities, but no matching
real-fluid Cantera validation was executed in this review. Our current use of
Cantera is an offline ideal-gas HP equilibrium seed, not a flame-speed result.

## Fuel-consumption speed: an independent balance check

This definition follows by integrating the steady species balance over a
planar travelling flame, with negligible diffusive species flux at the distant
fresh and burned boundaries:

\[
S_{c,F} =
\frac{-\int_{x_u}^{x_b}\dot\omega_F\,dx}
     {\rho_u(Y_{F,u}-Y_{F,b})}.
\]

`dot(omega_F)` is the signed net fuel mass production rate, negative for net
consumption. For a uniform-area finite-volume mesh, the numerator can be
evaluated as `-sum(omega_F * cellVolume)/area`. For rich mixtures, retain the
burned residual fuel `Y_F,b`; replacing the difference by `Y_F,u` assumes
complete fuel consumption. The integral must cover one whole flame. A domain
containing two equivalent fronts doubles the integral unless normalized by the
total flame area. During startup, inventory changes and boundary fluxes mean
the consumption measure need not equal the propagation measure.

This is a proposed independent diagnostic, not an already computed result and
not a second method attributed to Nguyen. Direct chemistry-rate output or a
fully closed species-inventory balance is needed. Temperature and OH profiles
alone are insufficient to claim a fuel-consumption result.

## Liang reference and inlet selection

Nguyen's reference [52] is W. Liang, W. Li, and C. K. Law,
*Laminar flame propagation in supercritical hydrogen/air and methane/air
mixtures*, Proceedings of the Combustion Institute 37 (2019), 1733–1739,
[DOI 10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070).
The [authors' institutional record](https://collaborate.princeton.edu/en/publications/laminar-flame-propagation-in-supercritical-hydrogenair-and-methan/)
confirms the publication identity. This review obtained the supplied Nguyen
full text and Liang's abstract/metadata, but not Liang's full implementation
description; details of modified PREMIX below are attributed to Nguyen.

Nguyen states that Liang used modified PREMIX, with the same chemistry and
real-fluid thermodynamics for this comparison but Ely–Hanley viscosity and
conductivity corrections instead of Chung. Figure 12 uses a solid curve for
Liang and symbols for Nguyen. Those are separate reference series; inlet values
must be digitized from **Liang's curve**, not Nguyen's symbols. The values are
approximate figure readings until machine-readable reference data are obtained.

Using the Liang values as inlet guesses should reduce front drift if the
predictions agree. It does not impose a successful replication: if the flame
moves, retain that correction, and report the computed speed separately from
the prescribed inlet. Since transport models differ, exact agreement with both
reference series is not an appropriate requirement. Store the crop identity,
axis calibration, digitized values, units, and reading uncertainty with the
case inputs.

## Reporting rule for this campaign

Report the OH density-weighted kinematic estimate as the primary Figure 12
comparison; add temperature-front/upstream-relative speed as a diagnostic.
Show the direct Equation (40) and fuel-consumption columns as unavailable until
their required source/flux outputs are implemented and checked. For every
number record the case/source/job, inlet guess, actual sampled time interval,
marker definition, unburned-density source, and fitting procedure. Check time
window, marker level, mesh, and domain sensitivity before calling a result
converged. Do not count several algebraically equivalent formulas as independent
validation methods.

Local evidence inspected: `state/paper-2022.txt`, lines 1194–1294 (Section 5.3
and Figure 12 discussion), extracted from the supplied
`1-s2.0-S0010465521003763-main.pdf`; and the pinned DeepFlame Git objects above.
No simulation, solver change, or compute submission was performed for this
source review.
