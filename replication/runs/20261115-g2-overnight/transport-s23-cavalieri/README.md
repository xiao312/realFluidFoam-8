# Species transport diagnostic S23

Frozen solver-only diagnostic build, parent S13 libraries unchanged. Inputs:
source.json/archive, exact parent runtime, original Cavalieri mesh/table/inlets.
Outputs: build/link qualification, fresh100us default-off profile regression
against S21, then a separate original-zero1ms predictor audit with Yi linear
tolerance1e-12. All other scalar/energy tolerances, chemistry, source clock,
time controls, clipping and acceptance remain unchanged. This is a numerical
accuracy diagnostic, not species renormalization, closure-species fitting or
scientific qualification. No library ABI change; all15 products remain pinned.

Plan through the FlamePilot adapter before admission. Inside Slurm, main.sh
checks every hash, builds with qualified multiarch flags and absolute library
paths, checks actual linkage/help, then runs the unchanged-default regression.
Only after that comparison passes does the fresh tight/audit case start.
Node syntax and strict Bash checks are preflight verification; only actual
solver results test predictor clipping, continuity and species sum failures.
Secrets/network/scheduler logic do not belong in this packet.
