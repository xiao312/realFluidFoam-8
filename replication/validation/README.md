# 2022 validation stages

This module owns reproducible property and laminar-flame inputs, execution, and
comparison. It does not qualify turbulent combustion or alter upstream physics.

Inputs are a verified source release, a successful isolated solver-build job,
the staged OF8 runtime, author thermochemistry files, and reference data with
recorded provenance. Outputs belong to `jobs/<id>` and `results/<id>` under the
configured project root. Private host profiles and credentials are never inputs
to the scientific code and never enter Git.

Dependencies: `environment/` for contained Slurm execution; the compiled real-fluid
libraries; Python 3 for deterministic case generation and numerical summaries.
Later application studies depend on the resulting evidence, not merely exit codes.
The runtime, build ID, source SHA, input hashes, commands, and scheduler limits
must accompany each result. Build products are reused read-only.

## Planned comparisons

1. Methane properties: SRK/rfJanaf/Chung at 1, 50, 100, 200, and 300 atm,
   180–620 K, matching the range in 2022 Figure 6. PR is an additional check.
   Compare density, Cp, viscosity, and conductivity with NIST WebBook tables.
   Preserve reference units; Cp in J/(g K) must be multiplied by 1000.
2. Axisymmetric counterflow: methane versus 21/79 mol% oxygen/carbon dioxide,
   300/1000 K, 1 and 200 atm, strain 100/s and equal inlet momentum fluxes.
   GRI30 and SEULEX; paper meshes and coarse development meshes are distinct.
   Methane/air at 100 atm additionally requires the cited case-6 conditions.
3. Planar premixed flame: methane/air, 100 atm, 298 K, GRI30, SRK/rfJanaf/Chung,
   central ignition, two outgoing fronts, waveTransmissive pressure, 0.5 micrometre
   paper grid. Report flame motion relative to gas velocity and the density
   weighting; do not equate laboratory front velocity with burning velocity.

Before inspecting results, use these engineering checks: finite positive bulk
properties, mass-fraction sums within 1e-8, and energy-to-temperature inversion
relative error below 1e-6. Report property relative RMS/max errors by pressure
without imposing an undocumented universal NIST agreement threshold. For flames,
target less than 1% temporal drift and less than 2% grid sensitivity in flame speed
and peak temperature before a quantitative comparison. These are project criteria,
not tolerances stated by the paper. Scientific acceptance still needs review.

The paper-era release differs from the current corrected OF8 source. Results here
test that declared port; they are not proof of byte-identical reproduction of OF6.
Missing benchmark arrays, domain extent, ignition details, and OH-isoline choices
must remain explicit when reconstructing cases. Do not report development runs as
paper-resolution validation.

## Minimal execution and verification

```sh
bash replication/validation/submit.sh plan ROOT IMAGE SOURCE BUILD_JOB properties PARTITION
bash replication/validation/submit.sh apply ROOT IMAGE SOURCE BUILD_JOB properties PARTITION
```

The plan is read-only. `BUILD_JOB` names a completed build inside the same root.
The stage runner refuses an absent build receipt and preserves all failed outputs.
Run Python syntax checks, shell syntax checks, and the generated case inventory
before submission. A property run must produce its CSV, library-resolution receipt,
and finite/inversion checks; a flame run also needs convergence and conservation
evidence before it is considered a completed comparison.
