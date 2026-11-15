# G2 source-clock controls

Responsibility: freeze and qualify an optional numerical relaxation-clock diagnostic, then compare paired original-zero G2 startup cases. This module does not fit chemistry or qualify developed LES/experimental agreement.

Inputs: immutable source archive d020b8df0d7ba6c9fd2306770bb08f08d5292773; qualified R54 parent build51075d5; existing53-species thermodynamics, target table92f947e2 and registered Schmitt/Cavalieri meshes. The source archive is generated with git archive on a case-sensitive Linux extraction. It is not stored here.

Outputs: actual compile/link/product receipts,40 executed source-probe rows, identical-alpha parity, invalid-clock rejection, and paired300us CFD fields, profiles and budgets. A failed case is retained and does not become accepted by a successful scheduler exit.

Configuration: default steps mode uses Cr100. The independent fixedTime diagnostic uses10us with unchanged maximum timestep5us/Co1. This is a convex Euler source update, not exact exponential integration; actual timestep/alpha histories must accompany comparison. Both modes start from the original pure-fuel zero fields. Source heating remains diagnostic only; absolute Ha is transported without adding chemical heat twice.

Dependencies: OF8 qualified environment f46b172c; FlamePilot Slurm adapter0d2a63b; fourteen pinned parent DSOs and one freshly compiled combustion DSO; freshly compiled reactingFoamSolveZ. The class layout/vtable is unchanged. Dynamic library realpaths/hashes are checked before physical tests. No source under core/hpc is modified.

Security: controller/SSH configuration and credentials stay outside Git. All generated files remain within D:/FlamePilot workspace or /public/home/dfagent/FlamePilot. ECS receives no bulk files. Scripts refuse existing case/build/output destinations and have preparation plan paths before mutation.

Example: create a packet from s01 plus the pinned git archive, generate LF SHA256 manifests, inspect its adapter plan, then submit s01/main.sh through FlamePilot Slurm. Only after actual build/probe qualification may either s02 packet be admitted. Do not execute compute on a login node.

Verification: bash -n each main.sh/run.sh; node --check each .mjs; sha256sum -c inputs.sha256 in the allocated environment; S01 requires15 pinned custom-library products and hashes/realpaths for each actually resolved custom DSO, successful help,40 passed rows with identical numerical values, and a specific negative-control rejection. S02 records actual exits/timezero hashes and preserves failures. Scientific acceptance remains false pending independent assessment.

Executed S01 qualification: job128102177 COMPLETED335s/0:0; source d020b8d; solver SHA25629ed7066d2d0b7ff84a4cffaee766fa46d7de31ab78595bfe3cca1991d720fa3. Inventory15 custom DSOs:14parent products and1fresh combustion. The solver actually loads14 of these (13parent+1fresh); the unused rhoReactionThermophysicalTransportModels product is retained/pinned but not falsely counted as loaded. Forty source-probe rows passed and equal-alpha modes were numerically identical; invalidtau was specifically rejected. This is build/source qualification, not CFD validation.

Active flow packets are source-clock-s02b-schmitt and source-clock-s02b-cavalieri. Earlier S02 is retained evidence: job128102594 FAILED202s before CFD, because the reused inlet helper accepts only the g2-relaxed- case prefix. S02b selects fresh compatible case names and otherwise preserves that helper and physics. Cavalieri S02 was never admitted. Corrected S02b actual admissions128102962/128103070 use32cores64GiB4000s each.

S03 thermodynamic queries completed361s with all24 inversions converged. Captured compositions recover1507/1496K and1984/2215K; target compositions at the same capturedHa recover3315–3400K. This supports composition/source-lag investigation at these hot cells; it does not qualify cryogenic inversion, chemical equilibrium, transported element conservation or the whole reacting CFD. See evidence-enthalpy-s03. Run `python plot-cell-queries.py RESULTS_ROOT` where that root contains hot-enthalpy-query-summary.json and hot-state-target-audit.json. Standard Matplotlib/NumPy only.
