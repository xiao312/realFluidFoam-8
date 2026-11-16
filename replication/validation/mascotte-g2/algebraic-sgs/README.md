# Algebraic SGS isolation diagnostic

This optional configurator replaces a fresh full-property kEpsilon preparation
with stock OF8 Smagorinsky algebraic viscosity. It isolates instability in the
transported turbulence equations without freezing eddy viscosity. It is not
three-dimensional LES, dynamic Smagorinsky, a PDF model or paper qualification.
The wedge filter scale and unity turbulent Lewis closure remain approximations.

Input: a fresh, undecomposed, not-yet-initialized direct-FGM case prepared by
`../rans-diagnostic` with full properties and kEpsilon. Output: changed momentum
and thermal-transport dictionaries, diagnostics and an explicit manifest override.
It retains the original turbulence preparation receipt, unused k/epsilon files,
initial nut, original chemistry, Ha equation, physical inputs and acceptance.
Smagorinsky computes k/epsilon algebraically rather than solving those files.
Prt=0.85 follows Sharma; the shared DEff=alphaEff operator also implies Sct=0.85,
which differs from the paper's Sct=0.7 and is recorded explicitly. No fitted constants.

Dependencies: Node built-ins and stock OF8 Smagorinsky/eddyDiffusivity at runtime.
Dependents: bounded scientific batches only. No network or secrets; apply requires
an admitted Slurm project case. Default is a read-only plan:

`node configure.mjs CASE [--apply]`

Verify Node syntax, actual fresh-case read-only behavior, rejection of optimized
Dimix suppression and evolved cases, then actual model selection, finite nonnegative
nut/alphat and unchanged enforcing caloric/coordinate/element gates in physical runs.
The RANS checker cannot qualify this different model; retain exact raw diagnostics.

`hot-kernel-control.json` declares a separate original-zero initialization
experiment: choose the maximum table temperature at fixed Z0.2 instead of the
maximum source. The table's existing eta knots are used without optimization
against paper curves. This tests the strong initial reaction transient of the
source-peak seed. It does not assert thermochemical equilibrium, alter kinetics,
introduce ongoing forcing or reuse cold/evolved states. Report actual selected
eta/C/T/Sc and retain the source-peak failure as its baseline.
