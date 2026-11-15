# Transported species with a relaxed table target

This model tests the species-relaxation operator in Schmitt (2020), Eq.12:
[doi:10.1007/s10494-019-00096-y](https://doi.org/10.1007/s10494-019-00096-y).
After a conservative pure-mixing species predictor Yplus, it applies
`Ynew = (1 - 1/Cr)*Yplus + Ye(Z)/Cr`. The paper selects Cr=100. This is an
explicit numerical relaxation toward a table target, not a fitted chemical rate.

## Source-clock diagnostic

The optional `relaxationMode fixedTime; relaxationTime SECONDS;` uses the Euler
fraction `alpha = deltaT/relaxationTime`. Omit `relaxationSteps` in this mode.
The default `steps` mode retains exactly `alpha = 1/Cr`, including the paper's
Cr100 choice. A fixed time is an investigation control, not an inferred chemical
rate or a claim that the paper is incorrect. Never select it by fitting a plot.

The fixed time must be positive and at least the executing timestep. This
preserves the convex source update without clipping or changing species bounds.
Use an explicit timestep ceiling no greater than the selected time. Both modes
report the applied alpha and time. No additional energy source is introduced.

`relaxationClock.H` owns this dictionary/math interface. It has no field, mesh,
scheduler or credential access. Inputs are coefficients and positive deltaT;
outputs are mode, alpha and time. Conflicting or invalid controls fail explicitly.
No existing class layout or virtual interface changes. Rebuild the combustion
implementation and solver against pinned parent libraries; identify all fifteen
resolved products, and verify default-mode parity before physical comparisons.

Verification uses the real one-cell source recurrence, default/fixed-clock
matching-alpha parity, and fresh physical cases at matched timestep/source time.
The one-cell check cannot establish CFD or paper agreement. Retained hot-cell
states and source/energy/element diagnostics select subsequent experiments.

The target uses the existing strict steady-table reader. Initial experiments
retain the original finite-chi table to isolate the change from instantaneous
composition replacement. That target is not the paper's seven-species
equilibrium model. No beta-PDF, variance, WALE/LES or paper geometry is supplied
by this module. Those remain independent development/validation steps.

Inputs: `combustionModel relaxedTable; relaxedTableCoeffs { table ABSOLUTE_PATH;
relaxationSteps 100; lookupRoundoffPolicy endpoint64epsilon; }`, the original
Z and actual species fields, absolute-Ha controls, global Euler stepping and
laminar Fourier transport. Cr must be at least1 so the update is a convex
combination; Cr=1 is the instantaneous-target regression limit. Species/inlet
thermo coefficients and the original table are unchanged.

Outputs: actual transported/relaxed Y, diagnostic c=YCO+YCO2, target-temperature
`steadyTdiag`, and `relaxedTableQdot`. Qdot is computed from the formation
enthalpy change and is diagnostic in the absolute-Ha equation: it must not be
added a second time. Temperature remains the executing thermo inversion of
Ha minus chemical enthalpy. Actual species boundaries remain case-owned.

The solver transports Z before the pure-mixing species predictor for this
model. It then invokes `correctSpeciesAfterTransport` before the Ha solve.
Every PIMPLE predictor uses the same physical old-time Y: relaxation must not
be accumulated repeatedly on an already relaxed state within a time step.
The solver's existing species clipping is retained and must be disclosed;
the model adds no clipping or normalization. Species-sum/positivity checks and
source element-change diagnostics retain errors rather than repairing them.

Dependencies: OF8 ThermoCombustion, the strict `forgeSteady::Table` reader and
executing thermodynamics. Dependents: reactingFoamSolveZ. The new combustion
lifecycle virtual methods change the custom-library ABI. Rebuild and qualify
all15 DSOs and all dependent applications from one frozen source; never mix
old/new binaries. Existing model defaults preserve their previous behavior.

No credentials, network, scheduler or agent-runtime dependency occurs here.
Minimal example: prepare a new original-zero laminar table case, select this
model/Cr100 and absolute Ha, then run the qualified solver through Slurm.
Verification: compiled factory/help checks, source-algebra/constant-Ha diagnostic,
Cr1 instantaneous-limit comparison, passive cold control, and new time-zero
reacting G2 runs with mass/energy/source and caloric checks. A build, synthetic
check or process0 cannot establish physical or paper acceptance.
