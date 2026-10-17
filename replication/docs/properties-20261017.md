# Methane property comparison — 2026-10-17

Both SRK and PR sweeps produced 225 finite positive states at exact requested
temperatures. The independent enthalpy inversion check failed its declared 1e-6
relative-error criterion. This is a completed comparison, not an accepted
scientific qualification.

The grid is 180–620 K in 10 K increments at 1, 50, 100, 200 and 300 atm.
The actual registered `psiReactionThermo` models use rfJanaf and chungTaka,
with the author's pinned pure-methane coefficients. The reference is NIST
WebBook retrieved 2026-10-17; it is not the paper's 2017 snapshot. Cp is converted
from J/(g K) to J/(kg K). Enthalpy reference levels are not compared.

## NIST comparison

Relative RMS errors (%), SRK:

| Pressure (atm) | Density | Cp | Viscosity | Conductivity |
| --- | --- | --- | --- | --- |
| 1 | 0.009 | 0.225 | 0.627 | 2.545 |
| 50 | 2.619 | 4.059 | 3.439 | 8.882 |
| 100 | 3.138 | 2.776 | 3.106 | 8.378 |
| 200 | 3.116 | 1.795 | 2.975 | 5.592 |
| 300 | 2.565 | 1.710 | 3.563 | 3.531 |

The full SRK/PR RMS and maximum errors, including maximum-error temperatures,
are in `properties-20261017-summary.csv`. For SRK, the largest conductivity
deviation is 30.908% at 50 atm, 190 K; density and Cp deviations there are
14.566% and 19.577%. Agreement is less uniform near the critical region. PR is
not uniformly better: its viscosity deviation reaches 48.935% at 300 atm,
180 K. No undocumented universal agreement tolerance is imposed.

These results compare the current OF8 code with current NIST values. They do
not by themselves establish exact reproduction of the publication-era code or
reference dataset. The paper-resolution state sampling and supplementary data
still need reconciliation before asserting reproduction of every plotted curve.

## Inversion check retained as failed

Each state first perturbs the initial temperature by +0.5 K and recovers it from
the exact target enthalpy. The probe records the recovery error, then restores
the exact target temperature before measuring properties. It does not silently
loosen the tolerance or alter the upstream solver.

| EOS | Failed states / 225 | Max relative error | Max absolute error (K) |
| --- | --- | --- | --- |
| SRK | 185 | 9.01896e-5 | 0.0263853 |
| PR | 208 | 1.25814e-4 | 0.0483752 |

The maximum relative-error states are SRK 50 atm/270 K and PR 50 atm/190 K.
Maximum absolute-error states differ: SRK 200 atm/330 K and PR 300 atm/440 K.
Source inspection found a 1e-4 relative Newton-step tolerance and assignment of
the previous iterate after convergence in
`src/thermophysicalModels/specie/thermo/thermo/thermoI.H`. This is consistent with
the observed recovery errors, but no source correction or patched-model
qualification is claimed. Preserve this baseline for any later reviewed fix.

## Reproduction and evidence

- Build: job `124657926`, source `b1153ea9c64b9abf55f7be6c488549024c081279`.
- Sweep: job `124660240`, source `4aed44d63eb0254837644a939c9b5fbae034b8df`.
- Sweep resources: two CPUs, 20-minute limit, elapsed 56 s; Slurm FAILED 3:0
  intentionally represents the inversion check, while both CSVs are complete.
- Raw evidence: `results/properties-124660240-evidence.tar.gz` under the trial;
  SHA256 `adf7f71aca2864fab14a06e30abb794c29332e327ec7d6f27da33d0b340f99f1`.
- Local output: `state/properties-124660240-comparison` under the local project,
  including CSV errors, JSON provenance and SRK/PR PNG/PDF plots.
- Reference URLs and hashes: `validation/properties/nist-provenance.json`.
- Analysis: `compare.py SRK.csv PR.csv REFERENCE_DIR NEW_OUTPUT_DIR`, followed by
  `plot.py NEW_OUTPUT_DIR --project-root ROOT`. Plot environment pins are in
  `validation/properties/analysis-requirements.txt` (Python 3.14.6 on Windows).

Jobs `124659480` and `124659758` retain the original first-state failure and its
expanded diagnostic respectively. Fixtures verified unit conversion, exact
coverage and independent retention of failed inversion checks. They are tests,
not solver results.

The next runs are bounded counterflow startup/cost pilots. Full flame validation
still requires convergence, mesh sensitivity and reference-profile comparisons;
none of those is established by these property or build checks.
