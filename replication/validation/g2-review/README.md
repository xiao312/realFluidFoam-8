# G2 sampled-field review

This module renders retained OpenFOAM CSV samples beside Sharma Figure 4b.
It does not run a solver, fill missing data, assign scientific acceptance, or publish.
The paper panel contains **time-averaged axial temperature**, with separate fine
and finer grids. Its gray band marks experimental flame location, not temperature.
The original caption is retained in the review.

## Inputs and outputs

Run `python review.py --case CASE --reference sharma-fig4b.json --pdf PAPER
--out NEW_DIRECTORY`. The default prints an input/hash plan without writing.
Add `--apply` to write PNG/SVG figures, original panel, plotted CSVs, provenance
JSON and an HTML review. Existing output directories fail. Inputs remain unchanged.

`CASE/direct-g2-input.json` supplies the observation contract from
`mascotte-g2/direct-fgm`. The module reads named CSV headers in:

- `postProcessing/instantaneousProfiles/TIME/nearAxis*.csv` and `radialN*.csv`;
- optional `instantaneousImagePlane/TIME/midplane*.csv`;
- optional `timeMeanProfiles` and `timeMeanImagePlane`, using `TMean` and `OHMean`.

Profiles use `x` or `y` in metres. Image samples use `x,y,z` in metres and the
registered regular `imageGrid`. Missing fluid points remain masked. No triangular
interpolation, smoothing, or symmetry reflection invents data in omitted regions.
CSV fields are selected by header, not filename order. Conflicting duplicate
fields, nonfinite values, unknown radial indices and off-grid image points fail.
`OH` means species mass fraction; it is never relabeled as excited-state OH*.

By default, the latest available instant and mean times are selected independently.
Use repeated `--time SECONDS` to select explicit samples. Available categories
without those times are reported as missing, not silently replaced by another time.
Optional `direct-g2-result.json` retains completion, averaging and conservation
diagnostics. Mean counters are labeled as producer-reported and only attributed
to the report's matching time. A mean without counters remains visibly unverified.
No startup mean is called statistically converged.

The near-axis line is normally at `r=0.0001 m`; it is not the exact centerline.
`--x-origin-m VALUE` applies `x_plot = x_mesh - VALUE` to our data only.
The default is zero and explicitly states that no paper-origin alignment was
assumed. `--x-origin-note TEXT` records the basis for a selected offset.
Paper curves retain their own published coordinates. Instantaneous and mean
comparisons occupy separate panels. No paper RMS or acceptance threshold is inferred.

Optional `--run-record JSON` copies operator-supplied source, environment and job
metadata into provenance. It is a declared record, not independently authenticated
scheduler evidence. Every consumed file and plotting source receives a SHA256.
Allowed record fields are `job_id`, `job_ids`, `source_commit`, `solver_source`,
`case_source`, `environment_sha256`, `solver_sha256`, `library_sha256`, and `note`.
Unprovided runtime identities remain unknown. `--label TEXT` changes the case label.

## Dependencies and boundaries

Python, NumPy, Matplotlib and PyMuPDF in the local analysis environment are required.
The module consumes `mascotte-g2/direct-fgm` observations and the explicit
`mascotte-figures/sharma_centerline.py` extraction. It has no runtime solver,
FlamePilot service, network, credentials or scheduler dependency. Downloaded papers,
sampled data and rendered outputs stay outside Git. It supplies local review
artifacts; scientific and human acceptance remain separate.

## Example and verification

```sh
python replication/validation/g2-review/review.py --case /data/g2-case \
  --reference /data/references/sharma-fig4b.json --pdf /data/sharma.pdf \
  --out /data/review/g2-latest --x-origin-m 0 --apply
python -B -m unittest discover -s replication/validation/g2-review -p 'test_*.py'
```

Expected: actual samples retain their named quantities, times and coordinate
convention; all missing map cells remain masked. Tests use explicitly synthetic
parser fixtures only and cannot establish physical agreement. Final qualification
requires a render from actual CSV samples and visual inspection of every figure.
The fixed PDF and original-image hashes must match the reference JSON before use.

Paper temperature curves use lines and our raw sampled temperatures use markers,
following the owner comparison convention. No smoothing, fitted curve or
statistical interpretation is added. Verify by rendering actual retained profiles
and inspecting axial and all three radial panels.
