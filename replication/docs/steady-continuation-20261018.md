# Counterflow continuations toward steady flow — 18 October 2026

Jobs 124806101 (1 atm) and 124806108 (200 atm) are submitted for long fine-grid
continuations. They depend on successful completion of replay qualifications
124805217 and 124805218 respectively. The active replays were left running.
Slurm cancels an invalid dependency rather than launching from a failed case.
The [job register](steady-continuation-jobs-20261018.json) pins source, archive,
solver/library identity, resources and convergence criteria.

Each continuation requests 32 cores for 48 hours. This first pair reserves at
most 3,072 core-hours; additional automatic batches are not installed. The owner
authorized continuing toward convergence and previously permitted more compute.
An optional campaign-limit preference was requested; absent a response, this
first 48-hour pair is the stated bounded assumption.

The source replay must finish its 10-microsecond endpoint check before copying.
The continuation validates and hashes the actual saved fields and mesh, reuses
the verified solver binary, and retains the source checkpoint as the initial
convergence reference. It does not repeat mapped time zero. Adaptive maxCo=0.2
and maxDeltaT=1e-6 s are unchanged. Checkpoints every 10 microseconds retain three
outputs; runtime controls remain readable. A watcher requests writeNow after
46 solver wall hours, providing margin before the 48-hour scheduler limit.

The physical ceiling is 50 ms, five inverse-strain times for a=100/s. Reaching
that ceiling is not a convergence test. Project-selected steady-candidate criteria
compare all cell values across at least 10 ms: maximum temperature change 1 K,
velocity-component change 0.001 m/s, density change 0.1% of reference peak,
pressure change 0.001% of reference peak, and each species change below the larger
of 1e-8 and 0.1% of its reference peak. All 53 species must be bounded and normalized;
T/p/rho must be finite and positive, peak T above 1000 K, and net inlet/outlet
mass-flux imbalance below 0.1% of inflow. Three passing comparisons separated by
at least 1 ms request an early checkpointed stop. Failed windows reset the reference.
These thresholds are selected for this campaign; they are not reported paper settings.

A candidate still needs centerline/paper comparisons, energy-balance assessment,
mesh/time sensitivity and scientific review. Restart equivalence remains unqualified
because the solver rebuilds some thermodynamic caches at restart.

At the measured roughly 212–218 wall seconds per step and maximum 1-microsecond
step, the optimistic 48-hour advancement is about 0.8 ms; smaller Courant-limited
steps reduce it. Thus this batch may not span even the minimum observation window.
Steady-state ETA cannot be inferred from the requested allocation. Longer runtime
or a separately qualified performance improvement is likely required.

Verification: Python/shell syntax and whitespace checks passed. Synthetic tests
passed short-window rejection, identical fields, temperature drift, mass imbalance,
reference-copy hashes and atomic stop-control updates. The same tests passed with
cluster Python 3.8. Both remote dependency plans passed and scheduler read-back
confirmed 48 hours, 32 cores and the exact afterok dependencies. The actual long
continuation startup, saved outputs and steady checks remain pending.

Scheduler observation: on this site the replay's TimeMin/EndTime estimates
changed from 19 minutes to 79 minutes after it continued past the earlier
estimate at 23:59 CST; TimeLimit remained three hours. Do not interpret those
changing estimates as observed termination. The pending continuation TimeLimit
was verified as two days. Attempts to set TimeMin did not change its read-back.
