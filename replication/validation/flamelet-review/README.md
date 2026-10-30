# Flamelet diagnostic review

This module turns retained physical trajectories, lookup-table diagnostics and
explicit paper-image calibrations into a reproducible local review. It does not
run chemistry, submit jobs, approve a result or publish to the ladder. Its paper
digitizer extracts visible colored pixels; it does not fit missing points.
Hue filtering rejects cross-color antialiasing, connected components smaller than
the explicit pixel threshold are discarded, and ambiguous wide vertical columns
are recorded separately instead of averaging unrelated curves. These exclusions
leave gaps and their counts/coordinates are retained in the extraction JSON.

## Interface and boundaries

Run `python review.py --run RUN_DIR --table TABLE_DIR --references IMAGE_DIR
--out NEW_OUTPUT_DIR`. Omit `--apply` to print a read-only input/hash plan. The run
directory must contain `trajectory.npz`, `receipt.json`, `diagnostics.json` and
`phase-metadata.json`; the table directory must contain `table.json`,
`coverage.json`, `heldout.json` and its `receipt.json`. All consumed result files
are verified against the producer's receipt before rendering. The image directory
provides `sharma-fig2a.png` and `sharma-fig2b.png`. `--config` can select another
explicit calibration JSON with the same schema. `--apply` requires a new output
directory and writes PNG/SVG, extracted CSV/JSON, metrics, input/code hashes and
`index.html`. Existing runs and outputs are never modified.

Dependencies are Python, numpy, matplotlib and Pillow in the existing local
analysis environment. No network, Cantera runtime or HPC credentials are needed.
The module consumes `fgm/direct-flamelet` artifacts and provides review artifacts
to the owner or the ladder publisher; it is not a solver dependency. Paths are
CLI inputs, not hard-coded host configuration. Downloaded PDFs, images, raw data,
HTML and rendered plots remain outside Git.

## Scientific interpretation

The initial supported diagnostic uses GRI30 ideal-gas chemistry at 5.61 MPa with
both streams at 300 K. Sharma Figure 2 uses the Kong mechanism at 6 MPa. The paper
uses normalized progress `c=(Y_CO2+Y_CO)/(Y_CO2+Y_CO)_eq` (Equation 22, PDF page 39).
The trajectory plots apply this formula using the initial HP-equilibrium state at
each mixture fraction as the denominator. This is explicitly labeled because the
paper also discusses low-strain normalization and the operating conditions and
mechanism differ. The table uses local `eta=(C-C_min)/(C_max-C_min)` over sampled
coverage; this is not paper `c`. No paper RMS or pass/fail comparison is computed.
Each curve retains its original time order,
including reversals, and paper extraction leaves missing pixel columns as gaps.

The reported enthalpy-mixing error is the producer's diagnostic against linear
inlet enthalpy. A suspected energy-implementation issue must remain visible;
this plotter does not correct energy or infer that a completed integration is
qualified. Kinetic-rate cross-check error and table held-out source error are
reported separately because they test different parts of the pipeline. Positive
synthetic reader checks are not physical validation.

## Minimal example and verification

```bash
python replication/validation/flamelet-review/review.py \
  --run /data/spitfire-warm-r2 --table /data/spitfire-warm-r2-table \
  --references /data/paper-crops --out /data/reviews/warm-r2 --apply
```

Expected: all input hashes match, finite arrays are checked, the final physical
time is reported, and each colored reference curve has extracted points. Inspect
`digitization-*-overlay.png` against the original crops and review all figure
labels before sharing. A wrong receipt hash, malformed data shape or conflicting
output directory must fail. Run `python -m py_compile *.py` and `git diff --check`
for source verification. Rendering actual retained data, visually checking the
result and a tampered-receipt negative control qualify the plotting workflow;
they do not establish scientific acceptance.
