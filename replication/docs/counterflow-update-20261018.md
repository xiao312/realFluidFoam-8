# Counterflow comparison update, 18 October 2026

The latest retrieved GRI30 fields improve substantially on the historical
one-step initialization images. The 1 atm oxyfuel temperature profile is close
to the paper drawing; the 200 atm flame remains displaced. Neither is grid
converged. The 100 atm air continuation failed and has no new saved checkpoint.

Snapshot collection started at 21:20:20 Asia/Shanghai. It excludes the newest
common time of a running case. Each selected file was hashed and checked again
before archiving; all snapshots retain global processor cell addressing.

| Case | Job | Saved time | Sampled peak T | Approx. paper peak T | Peak position difference |
|---|---|---:|---:|---:|---:|
| Oxyfuel, 1 atm | 124767586 | 69 ms | 1968.5 K | 1983.7 K | +132.7 micrometres |
| Oxyfuel, 200 atm | 124767667 | 58 ms | 2232.4 K | 2273.5 K | -123.8 micrometres |
| Air, 100 atm, prior smoke | 124767482 | 0.1 ms | 2264.6 K | 2215.3 K | -151.7 micrometres |

Each case has 11,200 cells. Near-axis sampling radii are 0.1665 mm for the
20-mm cases and 0.04163 mm for the 5-mm case; these are cell-centre samples,
not exact r=0 evaluations. Paper temperatures are approximate vector
digitizations of the published red temperature curves, not author tables or
independent OPPDIF data. No axial shift was fitted to improve agreement.

On the paper's plotted axial interval, near-axis temperature RMS differences
are 13.35 K (1 atm) and 402.53 K (200 atm). Thus peak-temperature differences
of -0.77% and -1.81% alone conceal the substantial 200-atm position mismatch.
The whole-field temperature RMS changes over the last saved 0.5-ms intervals
are 0.04123 K and 0.01170 K, respectively. Small local-in-time changes do not
establish mesh convergence or reproduce the paper's case conditions exactly.

Air-100 full job 124767672 failed in chemistry at 0.18956 ms before its next
write. Figure 11 now displays the earlier successful smoke at 0.1 ms, explicitly
labelled as such. Its apparent peak similarity cannot support steady-flame
acceptance. No recovery or larger-mesh reacting job was launched in this update.

All fields use upstream `realFluidReactingFoam`, build 124657926, with case
release `b15fb0db8213e6a5243c0f55691080195276253e`. They are not results from
the new named development executable. The three paper-informed development
meshes passed mesh checks only, and are separate from these 11,200-cell runs.

## Artifacts and verification

- Snapshot: `state/counterflow-latest-20261018.tar.gz`, extracted under the
  matching state directory. `snapshot.json` records every field/mesh hash,
  selected times, job ID and validation-input source/build receipt.
- Output: `output/counterflow-20261018-latest/`; five-page
  `counterflow-paper-comparison.pdf`, paper-layout Figures 8–11, full-domain
  temperature comparison, near-axis CSVs and `data/summary.json`.
- Original paper figures and captions appear beside current images in the
  PDF and are retained in the existing Lark comparison grids.
- Scripts: `collect_counterflow.py`, `plot_paper2022.py`,
  `counterflow_report.py` under `replication/validation/figures/`.

Checks: unique complete global addressing; finite arrays; immutable file
hashes; true nonuniform axial mesh edges in contours; regular-grid interpolation
only for displayed streamlines; paper crop dimensions; five rendered PDF pages
visually inspected. The displayed air failure and coarse-mesh qualifications
remain on the figures themselves.
