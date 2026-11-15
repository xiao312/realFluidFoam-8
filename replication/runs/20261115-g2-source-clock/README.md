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
