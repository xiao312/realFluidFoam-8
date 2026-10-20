# Liang hydrogen Figures 2–7

This module reconstructs the hydrogen calculations in Liang, Li and Law (2019),
DOI 10.1016/j.proci.2018.06.070. It uses the cited Burke et al. (2012) mechanism,
not Cantera's bundled `h2o2.yaml`. It does not change production CFD solvers.

## Inputs, outputs and configuration

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

`flame INPUT CASE PHI OUTPUT [GUESS|-] [WIDTH_M] [TU_K]` runs 100-atm H2/air.
Cases are `1`, `2`, `3`, `3star`, `4`, and `5`. Cases 3–5 use the existing
total-enthalpy residual; 3star uses stock Cantera's temperature residual.
Nonideal chemistry uses the pressure-based adapter. Case 4/5 conductivity is the
explicit dense-increment diagnostic, not a verified reconstruction of Liang's
unpublished rich-H2 mixing modification. Case 5 uses bounded, Table-2-corrected
Takahashi binary diffusivities with mixture-averaged mole-gradient fluxes.
Soret and radiation are disabled; the paper does not specify them.
Default Tu=298 K is an assumption, not a reported value.

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
