# Bounded low-dimensional paper campaign

This module extends the original OF6 counterflow port to the two remaining
published conditions and runs the 2022 Figure 12 premixed equivalence-ratio sweep.
It preserves the qualified OF8 solver. It does not promise convergence within a
wall-time allocation or treat the author's coarse tutorial mesh as a paper mesh.

Inputs are a named JSON configuration in `cases/`, `smoke|full`, the pinned author
inputs, and the existing premixed generator. Outputs are fresh job-local cases,
hashed input manifests, logs, processor checkpoints and endpoint checks. Config
fields are `family` (counterflow or premixed), `condition` (oxy-200 or air-100 for
counterflow), and `phi`, `cells`, `length_m`, `kernel_width_m`, `delta_t_s` for
premixed cases. Ranks and allocation limits are fixed by family: counterflow uses
8 cores for 12 hours; premixed uses 4 cores for 8 hours. Smokes use 30 minutes.
All submissions reserve against the same 1,000 core-hour ledger, under a lock.

Dependencies: author-counterflow preparation/transfer, flame generators/property
probe, environment runner, Slurm and the qualified build. Dependents: convergence
assessment and figure extraction. No new solver, Cantera, DNN or GPU dependency.
No secrets are consumed; all writes stay inside the configured project root.

Counterflow keeps the author's 80 x 140, three-block wedge, numerics, tolerances
and one-step-to-GRI30 sequence. At 200 atm the domain is scaled to 5 x 5 mm;
inlet velocities are computed from runtime densities for strain 100/s and equal
momentum. At 100 atm, the 20 x 20 mm air case uses 300 K streams, methane 1 m/s
and matched inlet mass flux, as in the paper's reference case 6. The O2/N2 air
fractions use molecular weights from the pinned input. CO2 remains the solver's
closure species, preserving the author's thermochemistry configuration. These
are declared condition adaptations; the original tutorial supplies only 1 atm.
The meshes remain development meshes and need refinement before acceptance.

Premixed cases use the existing 100-atm, 298 K CH4/air GRI30 real-fluid generator,
central 1800 K ignition, and waveTransmissive pressure at both ends. The base
domain is 2 mm, kernel width 0.2 mm, spacing 0.5 micrometre (4,000 cells), and
dt=1e-8 s, targeting 1 ms. The 11 phi values are 0.90 through 1.40 by 0.05.
At phi=1.10, separate cases halve dt, halve spacing (and dt), or double domain
length at fixed spacing. Domain/kernel choices are reconstructed, not published.
Chemistry retains the previously qualified premixed tolerances (1e-8 absolute,
1e-6 relative), distinct from the author's counterflow relTol=0.1. Comparisons
must use density-weighted gas-relative OH displacement speed, not raw front speed.

DeepFlame revision `7cb3294b275525cb8829ada3d3fbc067ab9323eb` was inspected at
`examples/dfLowMachFoam/pytorch/oneD_freelyPropagation/{H2,C2H4}`. Its empty
transverse boundaries and planar mesh are useful references. Its inlet/outlet
flame setup, fuel mechanisms, Cantera/Torch chemistry and initial profiles are
not copied into this central-ignition methane paper experiment. No DeepFlame
source files are redistributed here.

## Verification and operation

`python3 -B prepare.py plan CASE_KEY OUTPUT smoke` validates the configuration and
prints resource/physics choices without writes. `apply` refuses existing output.
Run `bash -n run.sh` and `bash -n submit.sh`. Scheduled smokes must pass checkMesh,
both counterflow stages/transfer where relevant, and finite/species checks before
full jobs are submitted. Full results remain development results until temporal,
mesh, domain and reference-comparison checks pass. Processor checkpoints survive
wall-time termination; no automatic continuation is installed.

Example: `submit.sh plan ROOT IMAGE RELEASE BUILD oxy-200 smoke PARTITION 1000`.
Use `apply` only after reviewing the plan. Full submission additionally requires
a passed smoke job ID as the final argument. The caller must select a relevant
smoke; the smoke key/family and source are verified before submission.
