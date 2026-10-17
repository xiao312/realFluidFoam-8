# Original OF6 counterflow inputs on the qualified OF8 solver

This module adopts the author's 1-atm counterflow examples at
`danhnam11/realFluidThermophysicalModels-6` revision
`61f86014ef3f4277d04a348c83777d6a20d24cf3`. It replaces the reconstructed
counterflow campaign at the owner's request on 2026-10-17. It does not change
the qualified OF8 executable or claim reproduction before convergence checks.

## Inputs and outputs

`original/` contains text dictionaries and fields only, with original byte hashes
in `provenance.json`. Mesh binaries, dynamicCode and compiled artifacts are excluded.
`prepare.py plan|apply OUTPUT smoke|full` creates fresh `one-step` and `gri30`
cases. Full runs retain the original end times (0.13 and 0.07 s), 1 microsecond
timestep, 11,200-cell mesh, boundary conditions and chemistry tolerances. Smoke
runs use ten steps per phase solely to qualify startup and field transfer.

OF8 compatibility changes are explicit: `SRKchungTakaMixture` replaces
`SRKchungTakaReactingMixture`; thermo and reaction data are included in the OF8
dictionaries; `turbulenceProperties` becomes `momentumTransport`; the invoked
application is `realFluidReactingFoam`. Execution starts from fresh time zero.
Eight radial MPI partitions, 12-digit output and fixed immutable runtime controls
are operational changes. Original numerical schemes and tolerances are retained.

`transfer.py plan|apply SOURCE TARGET` transfers only internal T, p, U and the
five common species from the one-step endpoint to the GRI time-zero fields,
preserving GRI boundary conditions. Other species start at zero via Ydefault.
Energy and density are recomputed by GRI thermodynamics; one-step enthalpy is
not copied between mechanisms. Mesh coordinates and connectivity must agree.
The source endpoint must pass finite/bounded field checks. Endpoint completion
is not proof of steady state; full-phase histories must still be reviewed.

## Dependencies and boundaries

Dependencies: Python 3, OF8 container, qualified build, Slurm, existing environment
runner and the shared counterflow reservation ledger. `run.sh` is invoked by
`validation/inside.sh` after isolated solver/library verification. Outputs, logs,
temporary files and scheduler records stay under the configured project root.
No secrets, network credentials, external writes or solver modifications occur.
Dependent: later figure comparison and convergence assessment.

## Verification and example

Run `python3 -B prepare.py plan OUTPUT smoke` for read-only discovery, then apply
to a fresh output directory. Run `bash -n run.sh` and `bash -n submit.sh`.
The scheduled smoke must pass mesh checks, both solver exits, transfer validation,
and species/field checks. `submit.sh plan` reports resource reservation before
`apply`; all submissions count toward the existing 1,000 core-hour cap.

Use `submit.sh plan ROOT IMAGE RELEASE BUILD smoke PARTITION 1000` followed by
the same command with `apply`. Full mode reserves 96 core-hours (8 cores, 12 h).
Smoke reserves 4 core-hours (8 cores, 30 min). Do not submit full mode before
the smoke passes. Review one-step convergence before interpreting GRI results.
