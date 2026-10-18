# Interim single-front flame comparison, 18 October 2026

The two development cases give a density-weighted OH displacement estimate of
about **6.33 cm/s** at phi=1.10, versus approximately **6.8 cm/s** in the 2022
paper's Figure 12. This is about 7% lower. These are interim measurements, not
accepted flame speeds or a replicated equivalence-ratio curve.

Extraction began at 21:02:39 Asia/Shanghai. Both jobs were still running. The
newest common processor time was excluded to avoid a checkpoint being written;
all selected source fields were hashed before reading and rehashed afterward.
Global ordering uses cellProcAddressing, with complete unique coverage of 4000
cells and a checked uniform 0.5-micrometre mesh over 2 mm.

| Job | Inlet speed | Latest plotted time | OH=5e-5, final 50 us | Final 100 us |
|---|---:|---:|---:|---:|
| 124780751 | 0.10 m/s | 0.41 ms | 6.3298 cm/s | 6.3126 cm/s |
| 124780755 | 0.20 m/s | 0.37 ms | 6.3294 cm/s | 6.3213 cm/s |

Extra digits support repeatability, not physical accuracy. Across the three
fixed OH mass-fraction levels 2e-5, 5e-5 and 1e-4, the final 50-us estimates
range from 6.3247 to 6.3347 cm/s. The 100-us estimates range from 6.3113 to
6.3253 cm/s. Windows end at each case's plotted time; these are different
physical times, so their close agreement alone does not prove independence.

## Method and comparison limits

At each saved time, linearly interpolate the rising OH isoline before the
primary OH peak. Fit its position against time with a straight line over six
consecutive saved states (50 us), and separately eleven states (100 us).
Interpolate local axial velocity and density at the same isoline. Calculate
the window mean of `rho * (U - dx_front/dt) / rho_u`; the unburned density is
112.7998488854405 kg/m3 from the runtime real-fluid property probe.

Positive speed denotes propagation into the cold gas on the left. The lab-frame
front velocities at OH=5e-5 are 0.03735 and 0.13770 m/s; both fronts drift right
because the imposed inflows exceed their burning velocities. Reporting the
imposed inlet speed or the lab-frame front speed as flame speed would be wrong.
At OH=1e-4 a second rising crossing occurs in the product-relaxation region;
that crossing is explicitly excluded.

This kinematic measurement corresponds to a gas-relative, density-weighted
isoline displacement. It does not directly evaluate the paper's discrete
chemical/diffusive source expression in Eq. (40). Saved fields are 10 us apart;
smaller output intervals and a source-budget cross-check remain useful checks.
The local 50/100-us window agreement does not prove final steady convergence.

Figure 12 reports speeds, not premixed spatial profiles. Our temperature,
density, velocity, pressure and species plots are diagnostics; they are not
overlays of published 1-D profiles. The original paper figure and caption sit
beside the interim speed comparison in the PDF and existing Lark figure entry.
Paper red-square positions were approximately digitized from the inspected
owner-supplied crop. The phi=1.10 centroid maps to 6.807 cm/s, reported as about
6.8 cm/s because it is graphical data, not the author's numerical table.

The fronts have temperatures approximately 298 to 2230 K. Pressure departures
are below 0.00033% at these sampled states. The new initialization avoids the
old 3000 K ignition plateau. Front-aligned temperature and species profiles
nearly overlap, but the seed is still ideal-gas HP equilibrium rather than SRK
fugacity equilibrium. Seed, domain, mesh and time-step independence remain
unqualified. The remaining 7% difference has no established cause yet.

## Run and artifact identity

- Solver/case source: `4ae4c078ff3f1b85b7adfd488d6da3c80d5ef979`.
- Solver: `rfReactingFoam`, rename-only baseline of upstream
  `48506de20ce67f35279c5347b09dcd86865a4c39`; no algorithm correction yet.
- Both executable SHA256 values:
  `f2df3effff068d9acf08ee023dc73ec3137a619a32ceeed4b1539255b28e4f6e`.
- Qualified library build: job 124657926, source
  `b1153ea9c64b9abf55f7be6c488549024c081279`.
- Runtime SIF SHA256:
  `7d4e96e0b1a97a0b361cbaf808b6242fa0c576e5ee2a27cd6a9a514c59cb529e`.
- Snapshot SHA256:
  `eedbf8296f1d339f877516708e32d91ff8a9ca6eaa62c321d4ff6eb99f6d8cc7`.
- Local snapshot: `state/inlet-profiles-20261018.json`; contains case/seed input
  hashes, runtime density record, per-field hashes and binary identification.
- Local report: `output/inlet-profiles-20261018-2102/premixed-paper-comparison.pdf`.
  The same directory contains PNG/SVG plots, full-resolution profile CSVs,
  approximate digitized reference points, and summary.json.

Reproduce with `extract_inlet_profiles.py ROOT 124780751 124780755` over SSH
stdin, saving stdout locally, then
`plot_inlet_profiles.py PROJECT SNAPSHOT OUTPUT` in the pinned analysis venv.
Extraction writes nothing remotely and submits no computation. Existing jobs
continue unchanged. Original paper images and raw data stay outside Git.

Verification: complete global-cell coverage, finite fields and positive
temperature/pressure/density, unchanged source-field hashes, unique primary
front crossings, both marker/window checks, and visual review of all three
rendered PDF pages. No scientific acceptance is implied.
