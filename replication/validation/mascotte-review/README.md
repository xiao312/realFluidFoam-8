# G2 profile and morphology review inputs

This offline module prepares four existing catalogue targets for later G2 CFD
review. It does not submit jobs, change solver inputs, or award scientific
acceptance. It complements `../mascotte-figures` (Sharma Figure 4b); it does not
create new catalogue IDs or replace the fixed ladder.

Inputs are the owner's exact PDFs, `targets.json`, and optional sampled CFD
profiles with an explicit metadata sidecar. Outputs are original figure crops,
original captions, numerical paper curves, reusable plot instructions, and an
HTML review outside Git. `prepare.py --plan` verifies source identities without
writing. `--apply` requires a new output directory. Downloaded papers and their
images are never committed. There are no secrets or network dependencies.

The numerical extraction uses Cavalieri Figure 6's PDF vector paths, not an
optical image or a fitted reconstruction. All eighteen M1/M2/M3 curves are
retained. The 45 mm mean panel's temperature tick scale differs slightly from
its bounding frame; explicit tick coordinates prevent a roughly 1.5% scale
error. The plotted polylines are exactly the PDF path vertices, with no smoothing
or invented observations. Figure stroke width gives a conservative reading
uncertainty; it is not experimental uncertainty.

Schmitt Figure 21, Singla Figure 4(c,d), and Sharma Figure 9 retain their original
images and captions, with quantity-specific comparison contracts. Ground-state
OH mass fraction is not OH* emission. Singla (c) is line-of-sight emission and
(d) is an Abel-transformed emission/backlight composite. No numerical intensity
agreement is claimed without the appropriate measurement model and calibration.

Dependencies: Python 3, NumPy, Matplotlib, PyMuPDF. Dependents: the G2 ladder
review and future CFD sample exporter. The runtime solver has no dependency on
this module. The minimal command is:

```sh
python prepare.py --pdf-dir /data/mascotte --out /results/g2-targets --plan
python prepare.py --pdf-dir /data/mascotte --out /results/g2-targets --apply
```

For refreshing a numerical comparison, also supply `--cfd profiles.csv
--metadata sampling.json`. CSV columns are `station_mm`, `radial_mm`,
`T_mean_K`, and `T_rms_K`; missing RMS is an empty cell, never an invented zero.
Metadata must identify `source_commit`, `job_id`, `mesh_identity`,
`statistics_kind` (`instantaneous` or `reynolds_time_mean`),
`sampling_start_s`, `sampling_end_s`, `sample_count`, `injector_origin_m`, and
`origin_qualified`. Only stations 15, 45, and 70 mm are accepted. Instantaneous
profiles remain explicitly preliminary and do not populate RMS or mean-error
scores. An unqualified axial origin is displayed as a preparation limitation.

Verification: run against the four pinned PDFs, inspect the curve overlay and
original/caption pairs, and check `receipt.json`: eighteen vector paths, all
finite values, no changed input hashes. The tool checks path style, location,
and monotone radial coordinates. Supplying a modified PDF must fail before
output creation. An extraction pass is not solver validation. The paper's
60 ms/50 ms averaging windows remain later statistical targets and must not
block independent short-time numerical diagnostics.
