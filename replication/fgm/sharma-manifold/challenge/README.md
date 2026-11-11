# Sharma paper-curve development task

This package gives Famou a physical flamelet task and a fixed numerical evaluator.
It owns reference data, scoring and runtime qualification. It does not own CFD,
scientific acceptance, scheduler access or the original Famou closure experiment.

Inputs are runtime.json, the author mechanism, patched Spitfire source and raw
digitized CSV/JSON reference curves. No paper images or credentials are required.
Candidate programs accept `--config FILE --output FILE`. Outputs contain `curves`,
indexed by reference curve ID, each with strictly increasing `x` and matching `y`.
JSON null represents missing coverage; extrapolation is not scored as coverage.
Candidates also retain physical trajectories and their source/configuration hashes.

`evaluate.py --prediction result.json --out metrics.json` uses only Python's
standard library. It records every curve's dimensional RMSE, normalized RMSE,
coverage and aggregate score. `--plan` shows the fixed reference contract.
The evaluator never changes physical outputs or grants scientific acceptance.
`platform_evaluator.py` executes a candidate separately and returns these metrics.

Dependencies: physical execution needs Python 3.12, Cantera 3.2, NumPy 2.2.6,
SciPy, compiled Spitfire/Griffon, BLAS and LAPACK. Scoring has no scientific-library
dependency. This package never accesses HPC or secrets. A local build helper
changes only upstream build metadata, not physics, and retains the source identity.

Verification: reproduce the frozen baseline score, reject wrong-shaped/nonfinite
outputs, penalize missing coverage, and show zero error for the reference-as-input
fixture. That fixture tests arithmetic only; it is prohibited as a candidate.
Runtime qualification requires actual warm production-rate comparison and a small
cryogenic flamelet integration. Imports alone do not establish execution readiness.

The primary objective is Fig. 2 (eight labelled curves). Fig. 1 burnt temperature
and six species are secondary. Its unlabelled intermediate progress contours are
not assigned invented c values. Reference uncertainty and extraction provenance
remain in references/provenance.json. All scores are development rankings.
