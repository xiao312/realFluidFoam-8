# Real-fluid coupling and manifold-source development evidence

14 November 2026, Asia/Shanghai. This note distinguishes observed failures,
published demonstrations, recent preprints and proposed experiments. It is not
scientific qualification of our reacting solver.

## Current observations

The pressure-based controls repeatedly develop large pressure departures followed
by a discontinuity in the executing SRK h(p,T,Y) function. More inversion passes,
initial/old-time flux compatibility, upwind scalar transport and more outer
correctors did not remove the failures. A separate density-based double-flux
application completes all six 20ms contacts, but remains first order and explicitly
quasi-conservative. PIMPLE energy projection before pressure correction did not
transfer that success to mixed contacts.

R34 source fdde132 fixes a separate regression: a property-cache refresh must not
replace conservative transport density. Both G2 controls then complete100us;
Cavalieri's fresh longer case fails148.4425us, Schmitt130.2356us. The first-step
Z defect and the later caloric failure are separate failures, not one tolerance.

R35 property-only job128040819 uses the unchanged C6 library/probe, exact captured
53-species composition and stored enthalpy. At4.927408MPa, h jumps from
-257516.323 to-215048.968J/kg between159.373558738 and159.373568738K; density
changes515.789 to307.585kg/m3. The target-256317.477J/kg lies inside this sampled
jump. Six guesses/twelve correction passes retain about41268.502J/kg error.
At the prescribed5.61MPa the same target reaches161.385154893K with0.002623J/kg
error and passes the CFD caloric criterion, but narrowly fails the probe's
separate enthalpy-relative1e-8 test. Both query exits3 are retained. This supports
branch/pressure investigation; it is not proof of the correct physical phase.

## Primary sources and transfer limits

1. [Ma, Lv and Ihme2017, JCP](https://web.stanford.edu/group/ihmegroup/cgi-bin/MatthiasIhme/wp-content/papercite-data/pdf/ma2017entropy.pdf)
   demonstrate real-fluid double-flux treatment combined with an entropy-stable
   hybrid scheme. Frozen cell-local thermodynamic tangents matter; adding generic
   dissipation is insufficient. Our existing first-order application is a narrower
   adaptation and is not the complete high-order/entropy-stable method.
2. [Ma et al.2017, reacting FPV framework](https://arxiv.org/abs/1704.02639)
   describe real-fluid FPV with departure-function reconstruction away from the
   reference table pressure and temperature. This is directly relevant to
   retaining transported energy rather than replacing it with tabulated T.
   Their explicit compressible implementation is not a PIMPLE recipe.
3. [Terashima, Ly and Ihme2025, JCP](https://doi.org/10.1016/j.jcp.2024.113701)
   report fully conservative internal-energy/species fluxes with approximate
   pressure-equilibrium preservation. Publisher abstract and author preprint
   abstract inspected; full flux derivation still needs reading before coding.
   [Author preprint](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4747391).
4. [Coppola, Aiello and De Michele2026](https://arxiv.org/html/2605.03617v2)
   propose EOS-dependent mass/internal-energy fluxes preserving pressure
   equilibrium and conservation, with supercritical/transcritical examples.
   This is a preprint. Its stated inviscid discretization scope does not establish
   multispecies, reacting, diffusive PIMPLE compatibility.
5. [Streamline Numerics pressure-based double-flux guide](https://streamline-numerics-inc-loci-stream.readthedocs-hosted.com/en/stable/theory/appendices/appendix_double_flux.html)
   documents a consistent frozen surrogate across pressure and energy operators,
   receiving-cell energy fluxes and true-EOS synchronization. This is developer
   theory documentation, not independent validation. It helps identify why our
   isolated successful solver cannot be copied as an after-the-fact h projection.
6. [CoolProp cubic backend source](https://coolprop.org/_static/doxygen/html/_cubic_backend_8cpp_source.html)
   explicitly handles multiroot states with imposed phase or density guesses.
   [Its phase documentation](https://coolprop.org/coolprop/LowLevelAPI.html)
   warns that imposing the wrong phase can give incorrect properties. Numerical
   branch continuation and equilibrium phase selection must therefore be separate
   model choices, not a silent root change to make a target invertible.
7. [Kovaleva, Rieth and Chen2022 poster](https://orca.cardiff.ac.uk/id/eprint/151580/1/PROCI_22_poster.pdf)
   shows source interpolation errors when neighboring flamelets have different
   unnormalized progress-variable extents. It tests additional normalization and
   Z-spacing changes. Different fuel/conditions: a transferable diagnostic,
   not direct validation of our CH4/O2 table or permission to clip source signs.
8. [PETSc SNES manual](https://petsc.org/main/manual/snes/)
   provides mature line-search/trust-region globalization and domain-error
   handling. Adapt the residual-reduction principle only where the actual
   thermodynamic function is continuous; no root finder can bridge a genuine
   missing target interval.
9. [SUNDIALS ARKODE documentation](https://sundials.readthedocs.io/en/latest/arkode/Usage/User_callable.html)
   describes constraint-aware step rejection and recoverable RHS errors, and
   cautions against modifying the input state inside an RHS. This motivates
   bounded source substepping with conserved accepted states, rather than
   repairing a table or state by clipping. It does not correct a wrong source.

## Experiments and decisions

- First qualify sharper double-flux spatial reconstruction with MC-limited MUSCL
  while preserving the original first-order mode. Uniform-state roundoff, two
  first-order anchors, all six20ms cases, full EOS closure, p/U equilibrium and
  explicit energy defects remain required. This is not yet entropy stability.
- Derive a coupled pressure-based frozen energy/density operator before another
  double-flux/PIMPLE experiment. A density derivative alone or an energy
  projection at the wrong lifecycle stage already failed; do not repeat them.
- For inversion, inspect all cubic roots, mechanical stability, Gibbs/phase
  criteria and pressure trajectories at the captured states. Keep gas-root,
  continuation and equilibrium candidates explicitly distinguishable. No
  production root-policy change before a declared physical model and regression.
- For FGM sources, replay original held-out physical flamelets and classify error
  by interior/edge, local progress-coordinate extent, source zero/sign and the
  transformed source Jacobian. Compare native/normalized-coordinate lookup and
  physical trajectory integration. Preserve current failed points and held-out
  data. A lower aggregate interpolation error is insufficient if signs or
  ignition/extinction trajectories worsen.

The owner continuation ends15November2026 at11:59Shanghai. All CFD starts from
original timezero and all heavy computation uses FlamePilot Slurm. Scientific
agreement, independent review and human acceptance remain distinct.

## 23:40 implementation checkpoint: root selection and pressure Jacobian

R37 job128042612 completed the full ABI rebuild in1172s. Under the default
largest-root policy, the executing property and inversion CSVs are byte-identical
to R35. The opt-in homogeneous-Gibbs policy reduces the captured-cell enthalpy
error from41268.5025 to0.00554177J/kg; all six initial guesses pass the existing
CFD caloric check. The separate enthalpy-relative1e-8 probe test still fails,
including at original inlet pressure. That failure is preserved; this supports
a separately labelled CFD diagnostic, not unconditional property qualification.

A second diagnostic has been implemented but not yet compiled or executed:
compare pressure derivatives at fixed T and fixed h through the actual mixture.
At fixed composition, dh=Cp*dT+(1-T*alpha)/rho*dp and
alpha=-(d rho/d T)_p/rho. Thus beta_h=beta_T+alpha*(1-T*alpha)/Cp.
Using Cp-Cv=T*alpha^2/beta_T, the same identity becomes
beta_h=(Cv*beta_T+alpha)/Cp, avoiding subtraction of large near-critical terms.
Its ideal-gas limit is rho/p. This is a thermodynamic derivation, not proof
that the current caloric departure implementation obeys it numerically.

The new probe audit records actual rho and enthalpy inversions at p±delta_p,
three pressure-step sizes, Cp finite differences, caloric residuals and both
Jacobian errors. It changes no CFD pressure operator. If this fails, preserve
the branch/caloric inconsistency before considering any operator change.

The NASA Ames
[December2025 seminar](https://www.nas.nasa.gov/assets/nas/pdf/ams/2025/AMS_20251218_DeGrendele.pdf)
provides a further lead: exact pressure-equilibrium flux constraints can become
ill-conditioned near equal neighboring states; their proposed pseudoinverse
falls back to an approximate underlying scheme. This is a research presentation,
not an already qualified algorithm in our solver. The transferable lesson is
to measure conditioning and retain a consistent limiting scheme, rather than
blindly demanding an exact correction at a singular state.

## 15 November00:08: direct implementation references and negative CFD result

R38 root-policy-only CFD failed: Cavalieri148.4425us/526.456J/kg and
Schmitt92.9854us/31665.344J/kg caloric gaps. Root selection improves one captured
state but does not qualify the coupled solver. R40 captures the new failed
states for property-only branch queries; it is not a restart.

R39 job128044951 compiled/linked/executed the pressure-Jacobian probe. Of72rows,
65passed the original criteria:23/24 at1e-3 pressure step,24/24 at1e-4,18/24 at1e-5.
Cp finite differences remain close, while fine pressure differences amplify
millijoule enthalpy-inversion errors. Do not relabel the multi-step audit passed.
The matched1e-4 evidence supports a separately labelled CFD tangent experiment.

Actual [DeepFlame source](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/src/dfCanteraMixture/CanteraMixture.H)
implements nonideal psi with a backward pressure perturbation at held enthalpy,
relative step1e-4. Its [pressure equation](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/applications/solvers/dfLowMachFoam/pEqn.H)
uses an incremental correction and updates its separate density cache. That
cache layout differs from our psiThermo p*psi relation: copying psi globally
would give incorrect density. We instead test the analytic fixed-h tangent in
the existing offset operator while retaining exact held-h property refresh.
No DeepFlame code has been copied; source/license are read-only references.

[Zhang et al.2026 preprint](https://arxiv.org/html/2607.19241v1)
describes the same fixed-h closure and physics-aligned surrogate inputs. Its
cell-local prediction results do not establish end-to-end reacting G2 stability.
Improving surrogate speed before resolving branch and operator consistency
would accelerate the wrong calculation.

[Xu, Sun and Guo2026 CDHD](https://doi.org/10.1016/j.jcp.2026.114653)
uses primitive-variable pressure evolution with high-order dissipation and a
conservative shock branch. The full21page author PDF was retrieved and governing
equations/method introduction inspected; it is not ported here. Keep its energy
defect explicit. CUBENS pinb12332f uses conserved density/momentum/total energy
in RK3 and reconstructs secondary state from rho/internal energy after each
stage (src/rk3.f90), not a drop-in PIMPLE pressure update.

The [SUNDIALS IDA formulation](https://sundials.readthedocs.io/en/latest/ida/Mathematics_link.html)
provides a useful cross-field model: differential updates and algebraic
constraints require a consistent residual/Jacobian and initial state. Applied
here as a design principle, this means inspecting continuity, energy and EOS
closure together; a tiny linear residual in one equation does not prove the
coupled state is consistent. No IDA dependency or fully coupled solver has
been added.

## 15 November00:56: remaining branch failure and a separate model route

Both R42 G2 conditions completed fresh200us controls with the unchanged checks.
Cavalieri's separate original-zero full case failed234.802822439us at
p5.254686959MPa,T161.690168030K,storedh-227356.990012J/kg and
evaluatedh-232920.317933J/kg,Cp252721.829J/(kg K). The5563.328J/kg gap remains
failed. This is progress beyond the old148us barrier, not a solved coupling.
At the completed200us control, EOS/transport-density relative mismatch was
2.975e-6 after the final refresh; continuity residual5.36e-17kg/s and caloric
relative error1.88e-9 measure different constraints and cannot substitute for it.

The next original-state contacts explicitly test conservative density with
2/6/12 nonlinear outer iterations. If consistent coupled iterations reduce the
pressure/energy/EOS defects, test that setting in fresh G2 before introducing a
different model. Preserve pressure and velocity errors, not just completion.

A separately labelled alternative is a true low-Mach pressure split: fixed
thermodynamic p0 for EOS/enthalpy and a distinct mechanical pressure in momentum.
[PeleLMeX state documentation](https://amrex-combustion.github.io/PeleLMeX/manual/html/Implementation.html)
keeps thermodynamic and perturbational pressures separately. The older
[PeleLM model documentation](https://amrex-combustion.github.io/PeleLM/manual/html/Model.html)
describes an ideal-gas implementation, so this is architectural evidence,
not proof that its low-Mach solver already supplies our real-fluid closure.
[The2017 supercritical DNS formulation](https://deepblue.lib.umich.edu/bitstream/2027.42/143049/1/6.2017-0141.pdf)
demonstrates constant-thermodynamic-pressure real-fluid coupling, but explicitly
studies very low velocities rather than rocket combustion. Applicability to
our G2 conditions must be measured, not assumed.

Such a candidate would need a pressure Poisson equation with no mechanical-
pressure EOS tangent, thermal enthalpy transport without inconsistent kinetic/
dynamic-pressure terms, explicit output of BOTH pressures, conservation and
Mach/pressure-ratio diagnostics. It is not pressure clipping or permission to
pass a compressible-pressure target by plotting only constant p0. It is currently
a proposed model variant, not implemented, executed or qualified.
