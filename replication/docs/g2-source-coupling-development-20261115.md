# G2 source and conservative-flux development pass

15 November 2026, Asia/Shanghai. Experimental branch; no production merge or
scientific approval. All CFD cases began from original time zero. The prior
85-job campaign remains closed. No new execution was admitted after this
investigation's21:21:54 cutoff.

## Result

We obtained a completed refined Cavalieri1ms case and qualified exact frozen-
target source integration, but neither provides a validated G2 paper match.
The new conservative APEC prototype closes mass/energy budgets while producing
unacceptable pressure/velocity departures. Its purpose is a diagnostic comparison,
not a replacement for the reacting solver.

## Executed controls

| Control | Actual result | Interpretation |
| --- | --- | --- |
| S11 Schmitt, fixed10us Euler, maxdt0.5us;128109165 | Payload8400s timeout; last completed898us, SlurmFAILED8566s | Crossed previous682us failure, but did not complete1ms; not a new numerical rejection |
| S12 Cavalieri, same refined clock;128109186 | COMPLETED5251s,1ms, global Tmax3322.735K; caloric residual2.394e-9 <1e-8 | Startup completion; energy/element and paper agreement remain open |
| S13 exact-source qualification;128112392 | COMPLETED320s; default20rows unchanged;60exact model rows; equal-time endpoint difference1.364e-12K | Exact frozen-target integration qualified; zero CFD steps |
| S14 fresh Cavalieri coarse exact clock;128112669 | FAILED545s at156.806us;3933.44J/kg caloric mismatch,162.579K,5.255MPa | Exact integration alone does not fix coarse G2 |
| S15/S15b fresh Schmitt exact clock;128112963/128113190 | First attempt failed beforeCFD from stale setup prefix; corrected fresh run failed1090s at229.427us with4085.14J/kg mismatch | Separate operator setup failure from actual cold-state caloric failure |
| S16 conservative APEC oxygen contacts;128113043 | Uniform control passed. nx4/6 completed20ms; nx2 stopped at an infeasible Newton seed | Completed cases conserve mass/energy near3e-13 relative, but pressure departures7.16%/4.72%; numerical equilibrium qualification failed |
| S17 central baseline and fixed-width refinement;128113312 | Baseline stopped at seed refusal;800cells completed20ms with11.43% pressure departure;1600cells payloadtimeout after at least19.625ms, last saved15ms | Refinement has not established satisfactory pressure equilibrium; partial-time fields are not20ms results |
| S18 seed globalization;128113699 | FAILED281s after uniform control passed; baseline and APEC failed rho/e convergence | Initial-seed refusal removed, underlying recovery still unresolved; no accepted-state criteria changed |

S18 retains actual target states: baseline rho327.775166kg/m3,
e=-233838.211J/kg, remaining residual249.628J/kg near153.503K/4.869MPa;
APEC rho351.205912kg/m3,e=-236969.328J/kg, remaining residual25.730J/kg near
154.296K/4.994MPa. These failures do not prove that no homogeneous solution exists
or that a phase flash is mandatory. An independent admissibility/phase diagnostic
is needed. No energy projection, root-check waiver or fitted coefficient was used.

## Paper comparisons and budgets

At the same1ms, S12 raises the Cavalieri radial15mm peak from412K in the older
Cr100adaptive control to813K; paper mean curves peak near1800K. Downstream45/70mm
profiles remain near288K. The near-axis maximum changes differently, so a single
peak is not a sufficient improvement metric. This is instantaneous startup
against developed paper means, not statistical replication.

Measured S12 Euler-consistent global mass closure is-1.49e-14 relative. Accepted
enthalpy change is4.070823J, while its assembled-equation/accepted-state mismatch
is+0.004279J. This is not an independently closed physical boundary-energy budget.
Final source-element maxchange2.45e-6 and EOS/transported-density mismatch1.93e-6
remain unresolved. Caloric closure does not qualify these other quantities.

The local Forge catalogue retains75targets/12papers, original captions and
primary images. Added S12 paper profiles/raw-cell temperature field, S16 contact
comparisons and S17 refinement views, including full-domain/full-range companions.
Paper traces are lines; raw computed samples are markers. Failed or timed-out
partial samples are labelled and excluded from same-time paper RMS calculations.
No GitHub Pages scientific publication or Lark update is claimed for this pass.

## What changed

The optional fixedTimeExact clock uses alpha=-expm1(-dt/tau). Default per-step
and Euler modes remain available. It integrates only a frozen source target
exactly; it cannot repair source elemental inconsistency or coupling errors.

The isolated oxygen-only APEC application adapts the public Trixi flux with
attribution/MIT notice. It evolves shared conservative mass/momentum/energy
fluxes and recovers actual SRK rho/e states without double-flux energy resets.
It does not implement multicomponent APEC, reacting FGM, turbulence or diffusion.
The accepted EOS/root and energy checks remain unchanged when seeding is repaired.

Fifteen library products remain pinned: S13 rebuilt combustion and reused14
qualified parent products; APEC trials compiled two applications against those
products. Parent thermo source51075d5 and environment f46b172c are unchanged.
Exact source/binary hashes are in qualification-summary.json. All submissions
used the pinned FlamePilot Slurm adapter0d2a63b. No subagents were used.

## Failures retained and next decision

The repeated G2 corner is cold, oxygen-rich material with small product fractions
near the injector and highly sensitive caloric behavior. Changing the source
clock did not remove it. Conservative pressure-equilibrium tests separately
expose pressure waves and near-critical recovery problems. These are related
hypotheses, not proof that one local solver change explains both.

Next priorities are: (1) matched-coefficient property/derivative and phase-
admissibility checks at the retained states, beginning with pure oxygen where
independent references are easier; (2) consistent pressure/enthalpy or a quantified
quasi-conservative formulation, informed by PEQSI/double-flux, compared on the
same contacts and fresh G2 diagnostics; (3) longer G2 statistics only after the
chosen method has acceptable pressure, mass/energy and source behavior. Keep
independent diagnostics progressing while failed targets remain visibly failed.
The current central APEC adaptation is not promoted just because it conserves
energy. Its full-interface derivative and stabilization choices still need audit
before attributing its behavior to the published method.

Operator packaging defects were preserved separately: an unsubmitted CRLF manifest,
a stale case-prefix helper, inherited historical runtime-receipt hash (corrected
and rerendered), and leading-decimal JSON in S16/S17 result wrappers. Raw receipts
remain immutable; explicit reader normalization and later source-format repairs
are recorded. None is labelled a scientific success or a solver compiler failure.

## Resources and current state

All23new admissions are terminal, consuming206.512778allocated core-hours.
Together with the retained85jobs/475.533889core-hours, cumulative usage is108jobs
and682.046667allocated core-hours. No active or pending campaign compute remains.
Large raw fields/logs stay on SCNet; only selected small exports were brought toD:,
with no bulk ECS transfer. The entire validation ladder remains incomplete.
