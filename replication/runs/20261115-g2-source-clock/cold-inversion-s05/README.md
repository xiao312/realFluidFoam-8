# Captured cold-state inversion diagnostic

Responsibility: query the exact failed Cavalieri composition/pressure/enthalpy through the qualified executing library. No CFD, changed chemistry, tolerance change, temperature clamp or evolved-state restart.

Inputs: retained rank0 cell50 at161.809312111us, full53 species and exact dictionary. Outputs:12-pass and50-pass enthalpy inversions from four guesses, and a separate temperature scan. Every numerical exit and partial CSV is retained; wrapper completion means delivery only. Dependencies: existing R54 probe/build and FlamePilot Slurm. Secrets stay outside the packet. All preparation has a read-only plan.

Verification: Node syntax checks, Bash syntax, SHA256 manifests and exact parent runtime hashes. Successful target recovery requires the unchanged1e-8 caloric/enthalpy criteria. A discontinuity or repeated unsuccessful inversion remains failed. Run all property compute through Slurm.
