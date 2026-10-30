# Source audit before direct energy and transport verification

Baseline: `a1f949e2212f28e1b0486df02bd85bedc0ed3a48`.

The retained MASCOTTE diagnostic's reconstructed energy residual is 0.0388391 J
over 30 microseconds, or 8.62% of the inferred enthalpy change. That result
remains failed. It does not by itself identify an error in the solved energy
equation: the evaluator reconstructed rho and sensible enthalpy from sparse
saved fields, used endpoint pressure, and omitted the assembled heat-transport
term. State after pressure correction is not the state at energy assembly.

The actual fork's `ThermophysicalTransportModels/laminar/Fourier/Fourier.C`
implements `divq(he) = -laplacian(alpha*thermo.alpha(), he)`. It is an
enthalpy-gradient closure. A temperature-only conduction estimate cannot bound
this term in a composition gradient. No missing species enthalpy term has yet
been established. The new diagnostic records the actual assembled diffusion,
convection, time derivative, kinetic and pressure-work terms separately. The
closed periodic test supplies a separate analytical energy expectation, so a
small linear residual alone cannot falsely qualify the physical energy update.

`momentumPredictor no` skips the momentum predictor solve; it does not disable
the pressure correction's velocity update. Earlier prose treating that switch
as no momentum dynamics was incorrect.

## Table interface findings

- The conservative progress equation is d(rho*c)/dt + transport = Sc. The
  reader's raw source is kg/m3/s. A second multiplication by rho is wrong.
- A normalized c uses Sc/dYc, with one global dYc. If dYc or the lower progress
  bound varies with Z, additional transport transformations are required. Use
  a mass-fraction progress variable for the first physical coupling.
- The table supplies internal species, Sc and Q; thermodynamics owns rho, T
  and h. Table temperature is only a diagnostic. Density is not a table output.
- `fgmTable::correct()` currently changes internal Y without evaluating species
  boundary conditions. The skipped species equations cannot refresh those
  boundaries. This needs a focused correction before variable-composition cases.
- The table lookup occurs before the c solve. Explicit source evaluation is
  intentional, but end-step composition and table diagnostics can lag the
  saved c. Refresh and source-time ownership need an explicit integration design.
- The fork's `StandardChemistryModel::Qdot()` uses minus the sum of species
  formation enthalpy times mass production. Cantera's total instantaneous heat
  release is not automatically the same source for a sensible-enthalpy equation.
  Physical exports must preserve this convention and the thermo reference state.
- The transonic branch's `phi == ...` is OpenFOAM's overloaded forced
  assignment, also present in the Foundation OF8 solver. It is not a C++
  equality-expression defect and must not be changed on that assumption.

The first verification deliberately fixes composition and uses analytic
sources. It qualifies neither chemistry nor the physical table's energy
coupling. It provides a fast falsifiable base before addressing those coupled
issues and the registered injector mesh.
