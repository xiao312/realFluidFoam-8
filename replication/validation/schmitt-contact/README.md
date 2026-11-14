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

The first contact baseline produced out-of-range inversion temperatures. The
next fresh control caps dt at5us (previous50us) and uses the existing three
fixed-enthalpy thermo inversion passes. Enable the unchanged1e-8 caloric audit.
These are numerical hypotheses, not a correction to the EOS or paper data;
preserve the failed baseline and compare its pressure/energy histories.

Optional --advection upwind selects a separately labelled first-order numerical
control. Default limited-linear retains the intended sharper baseline. Both
use identical EOS, profiles, timestep cap and caloric acceptance; compare all
six fresh cases to distinguish transport overshoot from thermo inversion.

The next density-continuity control selects conserveTransportDensity yes and
logs continuity before/after pressure density updates. This is a fresh candidate
against retained failures, not an accepted correction. Keep limited-linear
advection,5us cap, three thermo passes and the1e-8 caloric limit unchanged.


The separate configure-density-interpolation.mjs helper selects linear or
upwind-phi interpolation of rho in a new, uninitialized contact case. It changes
only the named interpolate(rho) scheme; species/energy convection, properties,
mesh and timestep stay unchanged. It prints before/after hashes without writes;
--apply requires SLURM_JOB_ID and rejects initialized/evolved cases or an existing
named rho scheme. It uses Node built-ins, no secrets or network. Example:
node configure-density-interpolation.mjs NEW_CASE upwind [--apply]. Verify syntax
and a read-only fixture, then run blockMesh/checkMesh/initializer/solver inside
Slurm. Test the actual FV scheme parser and pressure/temperature histories;
upwind numerical diffusion is a declared difference from AVBP TTGC/filtering.


A separate flux-consistency control pairs named upwind density interpolation with
upwind rho*U interpolation in Euler old-time flux correction. The official OF8
EulerDdtScheme uses dotInterpolate(Sf,rho.oldTime()*U.oldTime()); this is a distinct
lookup from interpolate(rho). configure-transport-consistency.mjs changes only
that named reference and the multivariate Yi_h convection entry, independently.
It prints a read-only plan; --apply requires a new uninitialized Slurm case.

writeConsistentContactMassFlux yes tells initializeSchmittContact to write fresh
phi from the executing initialized density, prescribed U and OpenFOAM's upwind
surface interpolation. This pairs the initial mass flux with the selected old-
time reference; it does not restart a CFD state or change initialization T,p,Y.
Default no preserves prior behavior. No separate mesh parser or property model is
introduced. Inputs/outputs stay within the new case, no network/secrets. Compile
with the exact parent libraries in Slurm, verify original versus compatible
initial flux and scalar-advection controls from zero, then20ms cases. This is an
Euler/static-mesh nonreacting contact diagnostic; no production FGM claim.

Primary source references (inspected2026-11-14):
https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/finiteVolume/ddtSchemes/EulerDdtScheme/EulerDdtScheme.C
https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/cfdTools/compressible/compressibleCreatePhi.H
