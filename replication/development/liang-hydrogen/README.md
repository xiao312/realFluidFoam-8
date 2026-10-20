# Liang hydrogen Figures 2–7

This module reconstructs the hydrogen calculations in Liang, Li and Law (2019),
DOI 10.1016/j.proci.2018.06.070. It uses the cited Burke et al. (2012) mechanism,
not Cantera's bundled `h2o2.yaml`. It does not change production CFD solvers.

## Inputs, outputs and configuration

`acquire.py plan|apply OUTPUT [--source-dir ORIGINALS]` downloads or reads
hash-pinned author kinetics, transport and CTI, performs strict Cantera 3.2
conversion, extracts the pair polynomials and compares both author formats at
54 prescribed states. It records the known malformed bibliographic-note repair.

`prepare.py plan|apply MECHANISM SPECIES_TABLE OUTPUT` validates a 13-species,
27-reaction author mechanism and a previously qualified SRK parameter table.
It writes immutable ideal/SRK YAML inputs, species parameters and a provenance
manifest. Downloaded author files stay outside public Git; their redistribution
license is not established. Source URLs and hashes are in the mechanism audit.
With `--pairs AUTHOR_PAIR_JSON`, preparation includes the ten applicable
quantum binary-diffusion polynomials in the author's appended transport block.
`HydrogenTransport.h` replaces those pressure-scaled binary coefficients before
mixture averaging and Takahashi correction; other pairs retain LJ transport.
Without `--pairs`, preparation makes an explicitly named LJ control.
Liang does not state whether his calculations enabled this author extension.
The polynomial temperature validity interval is not stated in the source.

`flame INPUT CASE PHI OUTPUT [GUESS|-] [WIDTH_M] [TU_K] [VARIANT] [GRID_FACTOR]`
runs 100-atm H2/air.
Cases are `1`, `2`, `3`, `3star`, `4`, and `5`. Cases 3–5 initially use the existing
total-enthalpy residual; baseline 3star uses stock Cantera's partial-enthalpy
temperature residual and is not established as Liang's Case 3* implementation.
Nonideal chemistry uses the pressure-based adapter. Case 4/5 conductivity is the
explicit dense-increment diagnostic, not a verified reconstruction of Liang's
unpublished rich-H2 mixing modification. Case 5 uses bounded, Table-2-corrected
Takahashi binary diffusivities with mixture-averaged mole-gradient fluxes.
Soret and radiation are disabled; the paper does not specify them.
Default Tu=298 K is an assumption, not a reported value.
The default `baseline` uses partial-molar species enthalpies in diffusion.
`pure-flux` instead uses pure-species SRK enthalpies there, reflecting Liang's
statement that mixture enthalpy differs from the mass-weighted species sum.
This is a named paper interpretation, not a change to the phase's thermodynamic
partial-molar API. `full-conductivity` uses the full unmodified Ely–Hanley model;
`pure-flux-full-conductivity` combines the two for a controlled diagnostic.
`matched-energy` uses total enthalpy with the same upstream advection stencil
as the species equations; `pure-flux-matched-energy` also changes diffusive
species enthalpies to their pure values. `pure-temperature` implements the
pure-species temperature approximation in Liang reference 8, including
Cp=sum(Y Cp_pure). Each energy variant is also usable with ideal Case 1 for
parity and grid tests. `EnergyFlows.h` owns these isolated energy residuals.
Prefix any variant with `smooth-` to select the already tested C4 continuation
of the Soave alpha function. This is a separately named diagnostic, not Liang's
reported model. It sets both phase and transport SRK evaluations consistently.
`GRID_FACTOR` is 1 (default), 2 or 4. Every interval of the initial grid is
subdivided by this factor before solving, while the same numerical guess is
interpolated onto it. This tests actual global grid refinement even when the
adaptive error criteria would otherwise retain nearly every initial node.
The original grid and final grid sizes are recorded. The grid limit rises to
12000 for this explicit refinement diagnostic.

An ideal HP equilibrium profile supplies only the initial steady-solver guess.
An optional solved CSV guess is also only a steady numerical initial guess.
No transient CFD checkpoint or restart is used. Each solve records grid
refinement, inlet speed, mass flux, outlet temperature, species and property
profiles. `transport.csv` compares ideal and real transport at identical T,p,X
along the solved flame, including H2, O2, N2 mixture and H2–N2/H2–O2 binary
diffusivity ratios. These definitions remain distinct because Figure 6 does not
identify a particular diffusivity.

## Dependencies and boundaries

The driver reuses `cantera-liang` SRK, transport, pressure-chemistry and energy
adapters and the pinned Cantera 3.2 SDK. Preparation uses Python/Cantera 3.2.
Builds and flames run through Slurm, one CPU per flame. `job.sh` confines HOME,
cache, temporary files and outputs to the project root. `submit.sh plan` is
read-only; `apply` submits an explicitly bounded build or solve. A completed
build and binary hash are required for solves. Failed jobs remain evidence.
No secrets are read or stored by the module. Site paths are command arguments.
The figure gallery consumes results; production solvers do not depend on them.

## Figure coverage and qualification

| Figure | Required calculation | Qualification limit |
| --- | --- | --- |
| 2 | H2/air and CH4/air mixture critical points | Reuse existing critical audit; Pc discrepancy remains unresolved and is independent of kinetics |
| 3 | Cases 1–5 plus 3star, phi=1–2.1 | Energy/transport implementations labelled explicitly |
| 4 | Cases 1/2, phi=0.6–3; fresh density and rho_u S_L | Unit conversion: kg/m3 /1000; kg/m2/s /10 |
| 5 | Cases 1/2/3/3star, phi=0.85–1.35 | Report flame endpoint, not substituted HP equilibrium |
| 6 | Stoichiometric transport ratios versus temperature | Show named diffusion definitions; no claim of unique paper identity |
| 7 | Stoichiometric T and H2/O2/HO2/H2O2 mole fractions | Translate x by a declared temperature marker; never stretch x |

First run phi=1 and 1.4 pilots. Require finite states, normalized species,
positive transport, convergence, and final speed change below 0.5% between the
last two grids before widening coverage. Domain-width and Tu sensitivity remain
separate checks. Grid refinement alone does not establish agreement with Liang.

## Minimal example and verification

```sh
python3 prepare.py plan /data/burke.yaml /data/species.txt /new/hydrogen-inputs
bash submit.sh plan ROOT RELEASE SDK INPUTS build - kshcnormal
bash submit.sh apply ROOT RELEASE SDK INPUTS build - kshcnormal
# After build qualification:
bash submit.sh plan ROOT RELEASE SDK INPUTS 1 BUILD kshcnormal 1.0
```

Run `python3 -B prepare.py --help`, `bash -n job.sh`, `bash -n submit.sh`,
and `git diff --check`. Build qualification runs the existing independent SRK,
alpha and Takahashi checks before compiling the hydrogen driver. Each flame
checks CP against finite differences and the partial-enthalpy Euler identity.
The ideal control must also agree with a separately solved stock Cantera flame
before treating discrepancies as nonideal model effects.
`stock_control.py plan|apply MECHANISM OUTPUT --phi 1.4` supplies that independent
Python control with the same final grid criteria and 6000-point limit.

`collect.py plan|apply JOBS_JSON SNAPSHOT --host SSH_ALIAS --root ROOT` performs
remote reads only and writes a new local snapshot plus scheduler state. Each job
row has `job`, `case`, `phi`, and `transport` (`lj` or `pairs`). Its resulting
manifest feeds `plot.py plan|apply PAPER MANIFEST CRITICAL_CSV SPECIES_TXT OUTPUT`.
The renderer uses NumPy/PyMuPDF, preserves source panels at publication scale,
adds open-symbol legends, and exports six PNGs, a PDF and evidence JSON.
Out-of-range samples are counted, not forced inside the original axes.
