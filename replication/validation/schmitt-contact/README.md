# Schmitt 2020 contact-advection baseline

Prepare fresh one-dimensional OF8 cases for Figures 5 and 6. Run the current
realFluidFoam solver without adding the paper's AVBP artificial-viscosity model.
The comparison measures our algorithm, not a claim that it implements AVBP.

Inputs: a real-fluid thermo export containing only O2 and H2, its manifest,
`oxygen` or `mixture`, and the paper interface width nx. Output: a new case,
input hashes, initial profiles and sampled rho/T/p/U/Y after20ms.
Domain reconstruction: x=-2..2m, dx=0.01m, empty transverse faces. Pressure6MPa,
velocity10m/s. Fig5 uses rho1000→100kg/m3 and nx2/4/6. Fig6 uses100K and an O2→H2
mass-fraction interface with nx1e-5/2/4. Exact erf profiles follow equations26–27.
The far boundaries use waveTransmissive pressure and outflow-compatible velocity,
temperature and species. Their relation to AVBP's nonreflecting treatment is an
explicit implementation difference. NASA polynomials below their original range
are declared extrapolations, inherited from the identified thermo export.

`prepare.mjs --thermo-dir DIR --kind oxygen --nx 2` prints a read-only plan.
Add `--out NEW_CASE` to write. Node built-ins only; no credentials or network.
`initialize.C` uses the actual linked OF8 thermo to invert the requested oxygen
density at fixed pressure. It writes the achieved initial density and mismatch.
It does not change EOS parameters or fit temperatures to paper curves.

Dependencies: `realfluid-g2-thermo` export, `fgm-of8/direct-verification` schemes,
the frozen full-fork runtime and reactingFoamSolveZ. No table closure or reactions
are selected. H2 and O2 formation enthalpies are zero; sensible h and absolute Ha
therefore have the same reference in this nonreacting test. This does not change
the reacting solver's absolute-Ha coupling policy.

Verification: `node --check prepare.mjs`; inspect all six read-only plans, exact
mesh spacing and erf limits. Inside Slurm compile the initializer, checkMesh,
verify initial density residuals, then execute and retain every case exit code.
Compare final fields, pressure/velocity departures, interface displacement and
runtime against the paper. Never infer scientific acceptance from normal exit.
