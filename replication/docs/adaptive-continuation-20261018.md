# Adaptive low-dimensional continuation, 18 October 2026

The owner requested adaptive timesteps and sufficiently long runs after all 17
fixed-step allocations timed out. The new campaign retains the qualified solver,
chemistry, meshes and boundary conditions. It changes time/output controls and
restarts from saved states in new job directories. Production allocation limits
are 48 hours per case, with jobs stopping when their physical end time is reached.

## OF8 reference and selected controls

The installed OF8 `reactingFoam/laminar/counterFlowFlame2D_GRI` tutorial uses
`adjustTimeStep yes`, `maxCo 0.4`, and `writeControl adjustableRunTime`.
Its [official controlDict](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/tutorials/combustion/reactingFoam/laminar/counterFlowFlame2D_GRI/system/controlDict)
was checked against the pinned runtime copy. Our controller uses the more
conservative existing maxCo target of 0.2. This is physical-time Euler stepping;
the LTS tutorial and localEuler settings are not used.

| Family | Initial dt | maxCo | maxDeltaT | Physical end time | Write interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Three GRI30 counterflows | 1e-6 s | 0.2 | 2e-5 s | 0.07 s GRI30 stage time | 5e-4 s |
| Premixed baseline and doubled domain | 1e-8 s | 0.2 | 2e-7 s | 1e-3 s | 1e-5 s |
| Premixed temporal sensitivity | 5e-9 s | 0.1 | 1e-7 s | 1e-3 s | 1e-5 s |
| Premixed refined mesh | 5e-9 s | 0.2 | 1e-7 s | 1e-3 s | 1e-5 s |

OF8 [setDeltaT.H](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/cfdTools/general/include/setDeltaT.H)
limits growth to at most 20% per step, reduces dt when required, and applies
maxDeltaT. AdjustableRunTime can further shorten a step to hit an output time.
The reported [compressible Courant number](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/cfdTools/compressible/compressibleCourantNo.H)
uses mass flux divided by density; it does not include sound speed or an explicit
chemistry/diffusion accuracy criterion. MaxCo is a controller target based on the
available flow field, not proof that no transient overshoot can occur. The log
prints Co before setDeltaT applies its correction; a printed value above maxCo
is not by itself the Courant number of the newly selected step.

The phi=1.10 temporal sensitivity case is now a half-maxCo/half-maxDeltaT experiment,
not the previous fixed half-dt experiment. This change must remain explicit when
comparing the two runs. Chemistry integration tolerances are unchanged.

## Restart and provenance

- Solver upstream: `48506de20ce67f35279c5347b09dcd86865a4c39`.
- Qualified build: job 124657926, source `b1153ea9c64b9abf55f7be6c488549024c081279`.
- Adaptive release: `b15fb0db8213e6a5243c0f55691080195276253e`.
- Release archive SHA-256: `ef823ad161eeb75541a2aa1f3e1b7725628cdcd04d76ba78b7520e0099c66344`.
- Runtime/SIF pins remain those in the environment lock and qualified build record.
- Source jobs, ranks and all controller settings are in
  `replication/validation/flames/adaptive/cases.json`.

The 1 atm counterflow resumes at saved GRI30 time 0.001 s. The 200 atm and air
counterflows start from their saved initialized GRI30 time zero; neither original
job saved its sub-millisecond GRI30 progress. Their completed one-step initialization
is retained through those inputs and is not rerun. Premixed restart times range
from 20 to 100 microseconds. Each new case records copied input hashes, origin,
checkpoint, control changes and finite/species checks in `case/restart.json`.

The original executable regenerates some internal caches on restart. In particular,
the species-enthalpy cache finding in the [cost audit](solver-cost-audit-20261018.md)
means an uninterrupted trajectory is not yet proven equivalent to a restart.
No physics fix was silently combined with the timestep change.

## Smoke checks and allocation

Every case must pass a short adaptive run before its full continuation is submitted:
0.0001 s for counterflow and 2e-6 s for premixed. Checks require End, adaptive
deltaT log entries, positive finite T/p/rho, all species bounded, and sum(Y) within
1e-8. They report T/CH4/OH changes; they do not qualify temporal accuracy.

Four initial fresh-stage smoke attempts failed in input validation before the
solver ran: startup species are supplied through Ydefault rather than individual
files, and rho may be absent until solver initialization. Releases `74b917f` and
`b15fb0d` corrected those input assumptions; endpoint validation still requires
all species and density. Existing saved-state smokes with identical configuration
and the same qualified build remain valid across these validator-only changes.
SCNet login nodes differ in Python availability, so submission explicitly loads
the installed `python/3.8.10` module. Simulation uses the pinned container Python.

Full allocations reserve at most 3,840 core-hours (80 cores across 17 jobs for
48 hours). The 21 smoke attempts reserve at most 56 additional core-hours, including
the four failed checks. This exceeds the original 1,000-core-hour limit under the
owner's subsequent authorization. The separate adaptive reservation ledger records
every submission. Allocation is a maximum, not a promise to consume all of it.

## Result qualification

Reaching 70 ms GRI30 time or 1 ms premixed time does not establish convergence.
Counterflow assessment needs changes in temperature/species profiles over saved
intervals and mesh/time sensitivity. Premixed assessment needs sustained front
propagation, density-weighted gas-relative burning velocity and mesh/time/domain
agreement. The 3000 K plateau remains an unresolved qualification issue.
The existing Lark figure panels stay labelled with their sampled time until new
fields are extracted and assessed; replace those panels in place when updating.

## Submission checkpoint

At 2026-10-18T13:21:27.800297+08:00, all 17 full continuations were RUNNING with
48-hour limits. Every case had passed its scheduled startup check. The
[job register](adaptive-jobs-20261018.json) records full jobs, all 21 smoke
attempts, source revisions, origin cases, controls and this status snapshot.
Log time denotes the latest entered step, not necessarily a written checkpoint.

Inspect saved profiles and progress again in 2–3 hours. Use measured advancement
over successive observations to estimate finish time; the startup ramp and changing
flow prevent a reliable campaign ETA from this first snapshot. Counterflow saves
every 0.5 ms and premixed every 10 microseconds. Extend physical targets only after
checking whether profiles or propagation are still developing, and keep every
continuation bounded and versioned. No scientific convergence is claimed here.
