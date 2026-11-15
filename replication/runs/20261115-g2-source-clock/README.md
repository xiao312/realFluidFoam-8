# G2 source-clock controls

This module freezes an optional numerical relaxation-clock diagnostic and compares paired G2 startup cases from original time zero. It does not fit chemistry or establish developed LES or experimental agreement.

## Inputs and outputs

Inputs are source `d020b8df0d7ba6c9fd2306770bb08f08d5292773`, the qualified R54 parent build `51075d5`, the existing 53-species thermodynamics, target table `92f947e2`, and registered Schmitt/Cavalieri meshes. Generate the source archive with `git archive`; extract it on case-sensitive Linux. The archive is not stored here.

Outputs include actual build and product receipts, 40 executed source-probe rows, equal-alpha parity, a specific invalid-clock rejection, and paired CFD profiles and budgets. Failed cases remain evidence. A successful scheduler exit does not establish scientific acceptance.

## Configuration

Default `steps` mode uses Cr = 100. The `fixedTime` diagnostic uses a 10 microsecond timescale, with maximum timestep 5 microseconds and Co = 1. Both cases start from original pure-fuel zero fields. Formation heat remains diagnostic; chemical heat is not added twice to the absolute-Ha equation.

The fixed-time update uses Euler relaxation, not exact exponential integration. Preserve actual timestep and alpha histories; finite-step error still needs assessment. The chosen timescale comes from the earlier fine-step Cr = 100 control, not temperature fitting.

## Dependencies and boundaries

The module uses the qualified OF8 environment `f46b172c` and FlamePilot Slurm adapter `0d2a63b`. It pins fourteen parent library products, compiles one new combustion library and compiles `reactingFoamSolveZ`. The combustion class layout and virtual interface are unchanged. Check every actually resolved custom library's realpath and hash before physical tests.

Credentials and controller/SSH configuration remain outside Git. Generated files stay in the D: workspace or `/public/home/dfagent/FlamePilot/`; ECS receives no bulk files. Scripts refuse existing destinations and provide preparation plans before mutation. Compilation, property queries and CFD run through Slurm, never on login nodes.

## Execution

Create an S01 packet from these scripts and the pinned source archive. Generate LF SHA256 manifests, inspect the adapter plan, and submit `source-clock-s01/main.sh` through FlamePilot Slurm. Only after actual build/source qualification may an S02b packet run.

The active physical packets are `source-clock-s02b-schmitt` and `source-clock-s02b-cavalieri`. Each executes a fresh Cr = 100 control and a separate fresh fixed-time case to 300 microseconds. Both retain the same mesh, boundaries, table, energy coupling and acceptance checks.

Earlier S02 packets are retained history. Job 128102594 failed before CFD because the reused inlet helper accepts only the `g2-relaxed-` case prefix. S02b uses compatible fresh names and preserves the helper. The original Cavalieri S02 packet was never admitted.

## Verification and retained results

Run `bash -n` on shell entrypoints and `node --check` on JavaScript files. In the allocated environment, run `sha256sum -c inputs.sha256`. S01 requires pinned product identities, successful help, 40 passing source-probe rows with equal numerical values, and the specific negative-control rejection.

Executed evidence:

- S01 job 128102177 completed in 335 seconds, exit 0. Solver SHA256: `29ed7066d2d0b7ff84a4cffaee766fa46d7de31ab78595bfe3cca1991d720fa3`.
- Fifteen custom library products are pinned. The solver loads fourteen: thirteen parent products and the fresh combustion library. The unused rho-reaction transport product is pinned but is not counted as loaded.
- All 40 source-probe rows passed. Equal-alpha modes produced identical numerical CSV values. The retained receipt's historical field name includes `Bitwise`; the comparison is numerical equality, not an independent IEEE-bit audit.
- The default fresh-CFD regression matched 32,000 values exactly against the retained baselines at actual time 20.4651195144 microseconds. No time interpolation was used.
- S03 job 128102509 completed in 361 seconds. All 24 enthalpy inversions converged. Captured compositions recover their original hot-cell temperatures; target compositions at the same captured Ha recover 3,315–3,400 K.

See `evidence-s01`, `evidence-default-cfd` and `evidence-enthalpy-s03`. These results support a source-lag investigation at the selected hot cells. They do not qualify cryogenic branches, transported element conservation, chemical equilibrium or the complete reacting CFD.

Run `python plot-cell-queries.py RESULTS_ROOT` with Matplotlib and NumPy. The results root must contain `hot-enthalpy-query-summary.json` and `hot-state-target-audit.json`. The figure distinguishes captured CFD temperatures from independent fixed-enthalpy property queries.

## Cold-state recovery experiments

The paired fixed-time Schmitt control reached 300 microseconds with a 3,254 K peak, versus 1,689 K in the same-time default. Cavalieri failed at 161.809 microseconds with a 7,565 J/kg caloric mismatch. The longer original-zero Schmitt fixed-time run failed at 682.083 microseconds with an 11,668 J/kg mismatch in cold oxygen-rich fluid. These are failed physical results, not accepted paper replications.

`cold-inversion-s05` and `cold-gibbs-s06` query the first retained failed state without advancing CFD. More inversion passes did not resolve it. The existing homogeneous-Gibbs root policy reduced but did not eliminate the fixed-pressure residual. This is a homogeneous cubic-root choice, not a phase-equilibrium flash.

`rho-ha-probe-s07` builds the field-independent solver recovery API from source 6a9a2ac. It passed 21 actual queries across seven fixtures: 15 expected accepts and six expected rejections. The failed Cavalieri transported density and Ha admit a stable, selected-root-consistent state if pressure responds by approximately +79.82 Pa. See `evidence-rho-ha-s07` and `evidence-cold-failures`. No failed-state archive is authorized as CFD initialization.

`coupled-solver-s08b` freezes source 842cd98 and rebuilds only the solver against S01's exact libraries. The original S08 build failed because a shared header lacked an include guard; the repair changes that guard only. S08b must pass build/link/help, product identities and default source parity. Build success is not CFD qualification.

`coupled-cavalieri-s09b` runs three independent original-zero cases: default/off regression, existing Gibbs policy alone, and Gibbs with the optional density/Ha predictor. The default regression must pass before new experiments. The two experimental cases retain the same source clock, mesh, boundaries, table and audits. They cannot be admitted before S08b is qualified. Runtime receipts determine actual delivery; scripts alone do not establish completion. Post-pressure predictions require another ordinary pressure solve and an unmodified final audit.

## Figure and evidence delivery

`plot-short-temperature-fields.py RESULTS_ROOT` plots actual cell polygons from the collected NumPy files, with fixed axes and a common color scale. Failed raw fields are labelled and never treated as valid thermodynamic solutions. There is no interpolated or reflected field data.

`import-investigation.mjs RESULTS_ROOT SITE CATALOG [--apply]` provides a read-only plan, validates the fixed 75-target/12-paper catalogue, preserves existing primary comparisons and captions, then adds diagnostic views and content-addressed evidence. It depends only on Node and the existing local Forge export schema; it has no HPC, model-provider or publication capability. Site/catalog writes are explicit and backed up. Verify every emitted asset by HTTP against its local bytes after applying. This is local ladder visibility, not independent acceptance or GitHub publication.


S08b actually completed in job 128107449,258seconds,exit0: solver SHA256
`5822d5252af9c0036dca8d5d88d5b41ecfc800738de7e39d39d9d78e1abff2d4`.
All 14resolved custom DSOs matched S01;40default source rows matched exactly.
S09b job 128107604 failed before CFD: its40us end rejected the100us field-output
interval. Its malformed numeric phase literal is also retained as a recipe defect,
not interpreted as physical evidence. `coupled-cavalieri-s09c` corrects that recipe
with a100us default/off run, preserving the original100us write interval and20us
sampling. The 300 us experiments and solver/runtime are unchanged. The actual
factory rejects the old configuration and accepts all three corrected configurations.
`schmitt-state-s10` queries the independently retained second cold failure using
S07's qualified property executable. This is separate from advancing CFD.


S09c job 128108126 delivered all three cases in 1218allocation seconds, wrapper exit 0.
The default100uscase completed and all 16,000 sampled values matched exactly at
the same physical time, 20.4651195144 microseconds. Both Gibbs-only and coupled experiments FAILED
at 141.918122745us with 8696.03J/kg caloric mismatch. The predictor rejected its
one candidate and changed no state. All 10000rawcelltemperatures were exactly
equal in thosefailed cases, peak3058.00K. The precise recovery rejection reason
was notlogged; do not infer it from the separate Schmitt property query.
See `evidence-coupled-cfd-s09c`. No candidate scientific acceptance or merge.

`temporal-s11-schmitt` and `temporal-s12-cavalieri` retain the original largest-root
EOS and fixed 10 usclock, reducing maximum timestep from 5 us to 0.5 us. Each starts from original time zero
and requests 1 ms; none restarts a saved state. Schmitt 17-digit and Cavalieri 12-digit
field formatting match their respective coarse references. Inputs and acceptance
are unchanged; extended final time exposes the previous failure points. These are
sensitivity tests, not established temporal convergence. Jobs128109165/128109186
are admitted; actual runtime/terminal receipts determine physical progress.
