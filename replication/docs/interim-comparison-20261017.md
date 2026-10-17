# Interim paper comparison, 17 October 2026

At 19:46:14 Asia/Shanghai, all 17 campaign jobs were RUNNING. Saved 20 ms
counterflow fields now support an interim comparison with 2022 Figures 8–11.
These are one-step initialization fields, not the developed GRI30 flames in the
paper. No replication error or acceptance score is reported.

A scheduler-only recheck at 19:55:27 confirmed all 17 jobs still RUNNING.
The plots remain tied to the saved checkpoints specified below.

| Case | Job | Peak T at 10 ms (K) | Peak T at 20 ms (K) | Whole-field RMS temperature change (K) |
| --- | --- | --- | --- | --- |
| Oxyfuel, 1 atm | 124672685 | 2023.89 | 2233.18 | 478.46 |
| Oxyfuel, 200 atm | 124674723 | 2000.00 | 2024.03 | 685.74 |
| Methane/air, 100 atm | 124674728 | 2000.10 | 2230.32 | 662.85 |

The large changes do not establish a steady solution. All three cases still use
the one-step mechanism; the scheduled GRI30 phase has not begun. Their 11,200-cell
author-style mesh is not the paper's demonstrated resolution. Nearest-axis cell
radii are 0.1665, 0.0416 and 0.1665 mm respectively.

The plots preserve the original panel arrangement and axis limits where possible.
Those limits can hide transient extrema; warnings and full-domain 10/20 ms
temperature profiles accompany the paper-scale panels. OH is absent from the
one-step mechanism and is omitted rather than represented by a zero curve.

Figure 12 still has no valid burning-velocity point. A separate ignition diagnostic
shows phi=1.10 job 124674599 at 10 microseconds: 621 of 4,000 cells are exactly
3000 K, and pressure spans 9.742–9.936 MPa against the nominal 10.1325 MPa.
The temperature plateau and pressure transient remain unresolved. Neither this
snapshot nor a transient laboratory-frame front speed establishes laminar burning
velocity. All fourteen premixed jobs reported a 3000 K maximum in the monitoring
sample; fixed time stepping does not enforce the configured maximum Courant number.

## Reproduction and evidence

The solver and environment are unchanged. Solver source is
`48506de20ce67f35279c5347b09dcd86865a4c39`; build source is
`b1153ea9c64b9abf55f7be6c488549024c081279`, build job 124657926.
The 1 atm case release is `59b99e85dd6908fa6ecb89615885ba2eb4a3e936`;
the remaining cases use `fecef1a844def139a6509687ed26310c988ca051`.
Input lineage and job limits are in the [campaign record](low-dimensional-campaign-20261017.md).
Environment pins remain in `replication/environment/lock.json`; the SIF SHA-256 is
`7d4e96e0b1a97a0b361cbaf808b6242fa0c576e5ee2a27cd6a9a514c59cb529e`.

Private workspace evidence, relative to the project root:

- `state/monitor-for-comparison.txt`: timestamped scheduler and log sample.
- `state/interim-counterflow-20261017.tar.gz`: mesh, processor addressing and
  saved 10/20 ms fields; SHA-256
  `7ff35bc4dd2cbeedf5a0e4eef8e0490b7003a895a62f8aed2d737d196a4529ea`.
- `state/checkpoint-review-20261017/phi110-10us-fields.csv`: premixed diagnostic.
- `output/interim-comparison-20261017-1946/`: six PNG/SVG plots, three assembled
  field archives, `summary.json` with hashes, and the six-page
  `realfluidfoam-interim-comparison.pdf`.

Run from the project root using the analysis environment:

```text
python -B repo/replication/validation/figures/plot_interim.py . state/interim-counterflow-20261017 output/interim-comparison-20261017-1946
```

Verification passed: every global cell is assigned once from processor addressing,
fields are finite, and the five one-step species sum to one within 1e-8. Mesh
centroids and nonuniform axial edges are used directly. Generation completed;
all six PDF pages were rendered and visually reviewed. These checks establish
data assembly and presentation, not scientific agreement.

The dated addendum places original figure and caption crops beside the current
plots. The previous all-figure atlas remains historical evidence. Source figures
and raw simulation data remain outside public Git.

Next: monitor completion of one-step initialization, inspect developed GRI30
profiles, and resolve the premixed plateau before extracting burning velocities.
No additional jobs or solver changes were made for this update.
