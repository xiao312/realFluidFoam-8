# Saved-sample G2 window statistics

This offline module computes explicit finite-window Reynolds means and RMS from
retained instantaneous sampled CSVs. Optional Favre statistics use actual
co-located density. It does not run CFD, fill missing samples, manufacture solver
`fieldAverage` counters, accept paper agreement, or establish statistical
convergence. Saved-sample statistics cannot resolve fluctuations between writes.

## Inputs, outputs and controls

The Node CLI requires `--case`, `--run-record`, `--start-s`, `--end-s`,
`--max-gap-s` and `--out`. `--favre` requests density-weighted means and RMS.
Default execution is read-only; `--apply` creates a new output directory.
The case contains `direct-g2-input.json` and the existing named instantaneous
profile/plane CSVs. The run record must identify `jobId`, source/runtime and a
finite `lastCompletedTime_s`. Data beyond that completed-time witness is rejected.

Within each named geometry, only actual sample times inside the requested window
are considered. An interval longer than the explicit maximum gap is omitted,
recorded and never bridged. No values are extrapolated to either window boundary.
Each endpoint of an included interval receives half its duration as quadrature
weight. Weighted means and central second moments therefore represent trapezoidal
quadrature of sampled statistics, not an assumed resolved continuous signal.
RMS is the square root of the weighted population central moment; no Bessel
correction or independent-sample assumption is used. Favre weights are those same
time weights multiplied by positive instantaneous density at each point.

All time slices must have exactly the same coordinate and field sets. Consistently
missing solid/outside points remain absent. Time-varying missing coordinates or
fields fail that input rather than generating replacement values. Repeated rows
at an identical coordinate may be removed only when every numeric field is
exactly equal; every removal is audited. Conflicting duplicates fail. Split field
files are joined by exact coordinates, not row order. One-snapshot or no-usable-
interval groups are explicitly unavailable and do not produce statistics.

Outputs are one compact CSV per available geometry, `manifest.json`, and a
duplicate audit. Fields are `TMean`, `TRMS`, etc.; with `--favre`, also
`TFavreMean`, `TFavreRMS`, etc. The manifest records requested and effective bounds,
used duration, coverage fraction, sample count, interval gaps, unmatched boundary
durations, all source hashes and the declared provenance. Partial interval coverage
is labelled as such; no full-window or statistically converged claim is inferred.

## Dependencies and boundaries

Node standard libraries only perform data operations. The optional Python paper
consumer uses NumPy, Matplotlib and PyMuPDF plus the existing `g2-review` and
`g2-paper-review` reference readers. It retains original crops/captions and marks
the curves as provisional saved-sample means/RMS. Schmitt's oxygen companion
retains the differing near-axis coordinate and85/288K versus83/300K conditions;
no normalized coordinate or numerical paper error is inferred from its crop.
Velocity comparisons remain unavailable without corresponding sampled velocity
and reference data.
No secrets, network clients, scheduler or publication calls enter this module.
All input snapshots remain read-only; derived outputs must be separate.

```sh
node replication/validation/g2-window-average/run.mjs \
  --case /retained/case --run-record /retained/run-record.json \
  --start-s 0.0001 --end-s 0.001 --max-gap-s 0.000025 \
  --favre --out /derived/window --apply
```

Render the retained statistics beside original paper captions and figures:

```sh
python replication/validation/g2-window-average/review.py \
  --statistics /derived/window --targets /references/g2-targets \
  --sharma-reference /references/sharma-fig4b.json --sharma-pdf /papers/sharma.pdf \
  --x-origin-m 0 --origin-note 'Qualified paper-exit companion; taper omitted' \
  --out /review/window --apply
```

The default paper view uses Reynolds statistics. Explicit `--weighting favre`
requires actual Favre columns and changes the labels; it does not assert that
the paper used the same weighting. No optical mean is inferred from these fields.
If no group has a usable time interval, `--apply` retains the unavailable manifest
and exits 2. A missing plane does not suppress available profile statistics.

Verification: `node --test replication/validation/g2-window-average/statistics.test.mjs`
checks the small mathematical contract and gap handling. Then run the read-only
plan and applied pipeline on retained real samples; verify coverage, duplicate
counts and output hashes and visually inspect the paper review. Short startup
data verifies the pipeline only, not a developed-flow paper comparison.
