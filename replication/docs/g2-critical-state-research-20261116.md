# Oxygen-rich G2 caloric failures —16November2026

Two fresh cases on the approved geometry reject oxygen-rich near-exit states around160K. Full-flow initialization fails at20.559us/p4.886MPa; a100us inlet ramp fails at59.225us/p5.101MPa. Executing Cp reaches15.6 and117.6MJ/(kgK). Repeated captured-state queries retain10.8–11.3kJ/kg caloric mismatches; conserved-density/Ha recovery returns negative dp/drho atfixedT. The exact query results remain failed. At nominal5.61MPa the fixed-p residual decreases to0.00255/0.00880J/kg; those targets still fail the replay's stricter energy-relative criterion. Smaller pressure excursions therefore help but do not establish a solution.

## Primary implementation references

[PelePhysics SRK](https://github.com/AMReX-Combustion/PelePhysics/blob/development/Source/Eos/SRK.H) expresses properties in density/T/composition coordinates. REY2T inverts internal energy at fixed density; its interface explicitly distinguishes conversions needing a second state variable. This supports investigating conserved-state recovery without assuming that fixed-pressure enthalpy has an admissible homogeneous root. It does not supply a VLE fix for our mixture.

[Cantera3.2 ThermoPhase](https://github.com/Cantera/cantera/blob/v3.2.0/src/thermo/ThermoPhase.cpp) limits Newton steps, maintains upper/lower energy observations, handles unstable heat capacity and restores the prior phase state on exceptions. These are useful numerical patterns. They cannot make a mechanically unstable homogeneous state stable.

[CoolProp flash implementation](https://github.com/CoolProp/CoolProp/blob/master/src/Backends/Helmholtz/FlashRoutines.cpp) separates phase-aware flash logic from single-phase inversion. Its documented PX path includes bracketed inversion and explicit residual/phase verification. A mixture phase-equilibrium treatment is a different physical model, not merely a larger iteration ceiling. We have not implemented or qualified one here.

[OF8 temperature inversion](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/thermophysicalModels/specie/thermo/thermo/thermoI.H) uses Newton temperature updates. Our retained fork additionally falls back to a temperature-width bisection. A small temperature bracket does not establish a small enthalpy residual across a phase-root discontinuity. The existing independent caloric check correctly retains these failures.

## Next controlled experiment

Select the existing constant-background low-Mach approximation in a separate original-zero genuine-FGM case: EOS p0=5.61MPa, projected mechanical pressure, thermal absolute Ha, unchanged table, geometry and caloric/species criteria. It deliberately omits acoustics and kinetic/dynamic-pressure-work contributions. It is not a fix of the compressible baseline and does not reclassify earlier failed contact tests. Measure both pressures, Mach, density consistency, mass/Ha budgets and temperature profiles. In parallel retain the cold source-paused control to distinguish mixing from reacting-product state effects. If captured roots remain inadmissible atp0, investigate phase-aware thermodynamics/manifold coverage rather than widening tolerances or fitting rates.

Source downloads and SHA256 receipts are retained in the operator workspace references/source-index.json. The PelePhysics development URL and CoolProp master URL are moving sources; this note records inspected implementation patterns, not a claim that a particular unpinned upstream revision was deployed.
