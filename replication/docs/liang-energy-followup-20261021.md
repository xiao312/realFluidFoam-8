# Liang energy follow-up: 21 October 2026

No additional physically required mixture-energy term was found. The new
overlap cases strengthen that conclusion: our consistent smooth temperature
and total-enthalpy formulations reproduce the plotted Case 3* temperature and
speed together, while Liang's Case 3 remains slower and slightly hotter.
Adding cooling cannot explain both quantities.

This note extends, rather than replaces, the
[earlier audit](liang-energy-formulation-audit-20261020.md). It checks continuum
terms, code paths and frozen states. No model, run, or parameter was changed.
The inspected checkout was `dcf1bd0d17ff646f43ff46d92d47af4f352cda36`;
the overlap runs used `cd62786661d050bcc9ea29023c8a1e3cd41ad41c`.

## Comparison at the same operating conditions

Values are from the completed `snapshot-overlap-0011` profiles and the
hash-pinned vector extraction. Reading allowances describe printed geometry;
they are not confidence intervals or experimental uncertainty.

| phi | Formulation | Speed, cm/s | Outlet temperature, K |
| --- | --- | ---: | ---: |
| 1.1 | Liang Case 3* | 57.1737 ± 0.3332 | 2448.645 ± 2.196 |
| 1.1 | Smooth partial-T, job 125071903 | 57.2646 | 2447.635 |
| 1.1 | Smooth matched-H, job 125071899 | 57.2727 | 2447.705 |
| 1.1 | Liang Case 3 | 52.1803 ± 0.3332 | 2451.929 ± 4.421 |
| 1.3 | Liang Case 3* | 72.8756 ± 0.3332 | 2347.859 ± 0.817 |
| 1.3 | Smooth partial-T, job 125071946 | 73.0570 | 2347.836 |
| 1.3 | Smooth matched-H, job 125071919 | 73.0636 | 2347.888 |
| 1.3 | Liang Case 3 | 68.8089 ± 0.3310 | 2351.865 ± 0.817 |

The original-alpha total-H controls give 57.2922/2448.557 at phi=1.1
and 73.0614/2348.557 at phi=1.3. Smoothing does not remove the speed gap.
At phi=1.3, our consistent solution is about 4 K colder than Liang Case 3
but 4.25 cm/s faster. The ideal baseline temperatures are 2460.959 and
2360.734 K at phi=1.1/1.3, versus paper values 2460.686 and 2360.705 K.
Thus a wholesale inlet-temperature or ideal caloric-data change is poorly
supported by these controls.

The consistent calculation's agreement with Case 3* does not identify the
unpublished Case 3* code. It does show that the additional Case 3 decrement
cannot be inferred merely by changing a valid temperature equation to an
equivalent enthalpy equation.
[Liang, Figures 3 and 5](https://doi.org/10.1016/j.proci.2018.06.070)

## Total enthalpy already contains the composition contribution

Write `m = rho*u`, `s_i = W_i*omega_i`, and use mass-specific species enthalpies.
The species equations and the expanded reference-8 energy equation are

```text
m Y_i' + j_i' = s_i

m (h' - sum(h_i Y_i')) - (lambda T')'
    + sum(j_i h_i') + sum(h_i s_i) = 0.
```

Substitution of the species equations gives exactly

```text
m h' + [-lambda T' + sum(j_i h_i)]' = 0.
```

This cancellation does not require `h = sum(Y_i h_i)`. In particular, a
separate advective "mixing enthalpy" source is not needed when the code already
differentiates the complete mixture h. Reference 8's equation therefore provides
no missing extra source to add to our total-H residual.
[Jorda Juanos and Sirignano, Eqs.4–5](https://sirignano.eng.uci.edu/theme/pdfs/39.pdf)

The implementation calls `SrkPhase::enthalpy_mass()` at each solution node.
Its value is the NASA ideal enthalpy, including formation enthalpy, plus Liang's
mixture departure. The gradient or upwind flux of that value includes the
composition dependence of molecular weight, a, b, molar volume and departure.
The diffusive flux uses the phase's partial enthalpies, or explicitly selected
pure-species values. Neither branch advects only sensible h.
[TotalEnthalpyFlow.h](../development/cantera-liang/TotalEnthalpyFlow.h),
[EnergyFlows.h](../development/liang-hydrogen/EnergyFlows.h),
[SrkPhase.h](../development/cantera-liang/SrkPhase.h)

With partial enthalpies, `dh = Cp*dT + sum(hbar_i*dY_i)` at fixed p.
For smooth properties, substitution gives the temperature residual implemented
by Cantera. The gradient of partial h includes composition derivatives;
Cantera computes it from adjacent full state values. A sensible-enthalpy
reformulation can also be equivalent, but it must move formation-enthalpy
transport into the corresponding chemical source. Adding that source to
the current total-h equation would count reaction heat twice.
[Cantera 3.2 Flow1D implementation](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/src/oneD/Flow1D.cpp),
[IdealGasPhase species enthalpies](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/src/thermo/IdealGasPhase.cpp)

## Pressure work and mechanical energy are not the missing correction

`Flow1D::setGas` and `setGasAtMidpoint` impose the same thermodynamic pressure
at every node. The enthalpy already contains p*v. The steady low-Mach energy
equation consequently has no additional nonzero `u*dp/dx` term. Starting from
internal energy would expose pressure dilatation; converting consistently
to enthalpy absorbs it. Reference 10 uses the same constant-pressure planar
enthalpy balance.
[Reference 10, Eqs.1–2](https://www.cmap.polytechnique.fr/~giovangi/688.pdf),
[Cantera governing equations](https://cantera.org/3.2/reference/onedim/governing-equations.html)

The actual saved velocity fields also bound the omitted kinetic-energy scale:

| phi | `(u_out^2-u_in^2)/2`, J/kg | Value divided by outlet Cp, K |
| --- | ---: | ---: |
| 1.0 | 4.30194 | 0.00248 |
| 1.4 | 11.97636 | 0.00632 |

This is orders of magnitude below the relevant caloric differences.
It supplies no plausible route to the measured speed gap.

## Reverse chemistry: distinguish consistency from replication

The pressure adapter delegates the complete net-source calculation to an ideal
phase. Its forward and reverse rates share the same concentrations and NASA
standard Gibbs energies. Changing the SRK caloric stage does not silently change
its reverse equilibrium constant. Cantera builds concentration equilibrium
constants from standard chemical potentials and standard concentrations;
the ideal pressure dependence cancels correctly.
[PressureChemistry.h](../development/cantera-liang/PressureChemistry.h),
[Cantera BulkKinetics](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/src/kinetics/BulkKinetics.cpp)

Fugacity-consistent chemistry is a physically motivated alternative, not a
correction to an omitted energy term. Reference 10 applies activity corrections
symmetrically to forward and reverse mass action. Modifying only a reverse
constant while retaining unmodified forward concentrations defines a different,
hybrid model. Liang does not publish enough kinetic implementation detail to
identify its choice from the citation alone.
[Reference 10, Sections 2.3 and 4.4](https://www.cmap.polytechnique.fr/~giovangi/688.pdf)

Independent frozen-state checks give a scale, without predicting a new flame:

- At the phi=1.4 heat-release peak, T=1734.705 K and Z=1.015519.
  Replacing ideal concentrations by actual SRK concentrations, including
  third bodies and falloff, changes the frozen ideal-enthalpy Qdot by -3.73%.
- At that same state, fugacity corrections to forward/reverse mass-action
  factors change Qdot by +2.07% when third-body/falloff prefactors are held fixed.
  This isolates mass action; it is not a complete nonideal kinetic closure.
- Full-domain integrals of these altered frozen sources are not flame-speed
  estimates: the saved downstream composition is no longer equilibrium for
  the changed law, producing domain-length-dependent residual heat release.

The equilibrium-temperature effect is much smaller. For each trial T, an
independent calculation iterated ideal TP equilibrium with chemical-potential
shifts `R*T*ln(phi_i)` until composition converged, then solved the SRK mixture
enthalpy constraint. The exact feed used 298 K, 100 atm and 21/79 O2/N2.

| Equivalence ratio | Pressure-chemistry equilibrium, K | Fugacity equilibrium, K | Change, K |
| --- | ---: | ---: | ---: |
| 1.1 | 2446.585805 | 2446.575969 | -0.009836 |
| 1.3 | 2346.813137 | 2346.806613 | -0.006524 |
| 1.4 | 2299.636013 | 2299.630681 | -0.005332 |

Elemental mass fractions were conserved within 2.5e-15 and the enthalpy residual
was below 1.2e-6 J/kg. The entropy offsets were used only for fixed-temperature
equilibrium iteration; they were not installed as a new thermodynamic model.
These values rule out a several-K equilibrium correction from this convention.
They do not bound its effect on flame speed or replace a converged flame test.

## What the discrepancy now supports

At phi=1.4, our Case 2 to consistent Case 3 change is -3.521 cm/s.
Liang's Case 2 to 3* change is -3.289 cm/s, followed by a second -3.663 cm/s
change from 3* to 3. The second decrement has no counterpart in the consistent
continuum conversion verified here. Matching it would require evidence of
another model/setup change, a different discrete implementation, or a problem
in the published calculation. The available article does not distinguish
these explanations, and this audit does not establish an author error.

The strongest next comparison is the complete original PREMIX residual and
stage-switch logic. Until that is available, preserve the consistent formulation
and label the discrepancy. The smooth T/H agreement, small pure-flux effect,
and matched-temperature overlap provide concrete tests that any proposed
"missing term" must pass before it is added.

## Reproduction inputs

Calculations used Python Cantera 3.2.0 and NumPy with immutable local profiles.
The mass-action probe evaluates the ideal phase at `(T,p,Y)` and `(T,p/Z,Y)`;
the activity-only probe multiplies each forward/reverse rate of progress by
`exp(sum(nu_reactant/product * ln(phi)))`, retaining its original prefactor.
Qdot is `-sum(h_ideal_molar * omega_net)`. Equilibrium uses the same independently
reconstructed original-alpha SRK kernel as the previous audit.

State root: `state/liang-hydrogen-20261020/`. Vector inputs and uncertainty
rules are in `digitized/reference.json` and `liang-hydrogen/digitize.py`.
The source-paper hash remains the one recorded in the previous audit.

| Snapshot / job | Profile SHA256 |
| --- | --- |
| snapshot-pilot / 125069048 | `e8603da7801be50fa87c5154cdc6a00aee6aca69e157688556535f87d500282e` |
| snapshot-pilot / 125069094 | `8e76f5711e4a1d63391f7e1318daa57e08f2a41e7a55deaf13d97a9a97e1d79f` |
| snapshot-overlap-0011 / 125071829 | `8542778bbbca439a3e172d1ebceb442ad3c37c4f7d6347e304ad44a77b7b6f4d` |
| snapshot-overlap-0011 / 125071904 | `bb83c6e2ab1d52b98e0ad7d2c26a54b41847130569084617e3a31ad952bcad32` |
| snapshot-overlap-0011 / 125071899 | `21f0c8c191891c3140e6b794e809fee64903b374a20529abb3f6f9f0bb29c112` |
| snapshot-overlap-0011 / 125071903 | `a2315767bc36dff04d87a95f19bed822bc40fb06db4d22e27b89dc537ec2e93c` |
| snapshot-overlap-0011 / 125071919 | `d2cd77bfae7f035d276f1fdbdc6f4f2360977245f55282bfc7441b4ef2b75b25` |
| snapshot-overlap-0011 / 125071946 | `e551f2a6a2ec4063dae3ed585c49f14f5771501f851e4dded054974bbc681a3c` |
