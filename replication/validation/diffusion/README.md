# Diffusion verification and validation

This module isolates the unresolved Liang Figure 8(a) Case 4-to-5 response.
It owns property fixtures, prescribed-state probes, and comparison gates. It does
not fit transport coefficients to flame speeds, alter production models, or accept
a model from one matching observable.

Inputs are the committed Liang results and digitization, author mechanism and
critical-property table, the pinned Cantera 3.2 SDK, and reference fixtures below.
Outputs are JSON gate reports and CSV property samples. Scripts print a read-only
plan by default; output files must be new. No credentials are used. Generated
files stay in the operator workspace or the configured SCNet project root.

Dependencies: Python 3 for reports, Cantera 3.2 Python for the dilute benchmark,
and the C++ SDK plus `development/cantera-liang/StagedTransport.h` for adapter
verification. The scheduler runner uses Bash, Slurm and GCC 11.2. Dependents are
the Case 5 investigation and comparison report. No solver depends on this module.

## Ladder and criteria

1. Replay the saved Case 5 disagreement with `flame_gate.py`. Exit 1 means the
   mismatch remains under the existing declared paper-comparison screen, not
   that the transport implementation has a proven coding bug.
2. Compare dilute CH4-N2 with McGivern and Manion, Table 2, at 101300 Pa.
   Compare every point to its reported 95% expanded uncertainty; do not introduce
   an extra model tolerance. CH4-air is a separately labelled exploratory check:
   the paper does not specify the exact breathing-air composition.
3. Verify the actual adapter against all 17 Takahashi Table 2 pressure nodes,
   intermediate pressures, and explicit range-policy samples. Relative tolerance
   is 1e-10. Deliberately disabling the Table 2 correction must fail this gate.
   This verifies code against a correlation; it is not experimental validation.
4. Qualify original high-pressure self/tracer/binary datasets before admitting
   them as fixtures. Require diffusion definition, composition, T, p, units and
   uncertainty. Suspect ThermoML scaling remains excluded.
5. At frozen flame states, check binary-to-mixture conversion, zero net mass
   flux, and species/pair contributions. Compare alternate mappings only when
   a property benchmark or source warrants them.
6. Run paired Cases 4/5 at phi=1.40 for a justified candidate, then phi=1.10,
   1.30 and 1.35 before the complete curve. Preserve chemistry, thermal models,
   critical data and mesh/domain criteria across each pair. Track both absolute
   speeds and their difference; retain digitization uncertainty. CFD runs, if
   needed later, must be original clean starts at time zero.

The original Takahashi pressure range is tabulated from Pr=0.1 to 5. The current
adapter's Pr<0.1 unity value, Pr>5 cap, and Tr clamp to [1,5] are policies to
report, not experimental claims. Paper curve agreement alone cannot identify
Liang's unpublished transport parameters.

`prepare.py INPUTS [--output NEW.csv]` plans/generates 798 prescribed states
for CH4-N2, H2-N2 and trace OH-N2. `property_probe.cpp` evaluates the actual
adapter and `check.py REQUESTS.csv SAMPLES.csv` checks factors to 1e-10 relative,
symmetry to 1e-12, and mixture reconstruction to 1e-7. The latter limit accounts
for subtractive cancellation in the near-pure bath; the existing ordinary flame
state reconstruction retains its 1e-10 limit. The probe also reports actual Pr/Tr
so floating-point crossings of the discontinuous Pr=0.1 policy are explicit.
Exactly-on-boundary samples are reported separately and must match either limiting
branch to the same factor tolerance. Additional Pr=0.09999999/0.10000001 samples
strictly check each side. This accounts for pair-normalization roundoff, without
changing the adapter or loosening any off-boundary comparison.
Prescribed correlation states can extend below a mechanism's fitted temperature
range; their dimensional dilute coefficients are not accepted property predictions.

Run `bash job.sh plan ROOT RELEASE SDK INPUTS PYTHON`, then submit `job.sh apply` with
those same inputs to Slurm (one CPU, ten-minute cap, explicit project log paths).
Expected: `corrected-report.json` passes and `legacy-report.json` fails when the
published Pr=3 correction is deliberately disabled. Preserve both reports.
`PYTHON` is an absolute, executable path under the broader FlamePilot project,
used read-only; its hash and version are recorded. Do not rely on the login-node
PATH being available on compute nodes.

## Minimal use and verification

From the repository root:

```text
python -B replication/validation/diffusion/flame_gate.py
python -B replication/validation/diffusion/dilute.py INPUTS/ideal.yaml
python -B replication/validation/diffusion/dilute.py INPUTS/ideal.yaml --output NEW.json
```

The first command is a deterministic saved-result replay and is expected to
exit 1 until the Case 5 discrepancy is resolved. The second prints the dilute
benchmark plan; the third performs the calculation and writes its evidence.
For a new screened flame dataset, pass `flame_gate.py --results RESULTS.json`;
it must include phi=1.30/1.35/1.40 so omitted failures cannot yield a passing gate.
Run `git diff --check`. For the C++ probe use `job.sh plan` before scheduler
submission; its documented positional inputs are ROOT RELEASE SDK INPUTS PYTHON.
The probe never solves a flame or changes an input file.

`plot.py DILUTE_REPORT REQUESTS.csv SAMPLES.csv [--output NEW_DIRECTORY]` adds an
optional NumPy/Matplotlib reporting dependency. Without `--output` it is read-only.
It produces PNG/PDF panels of measured dilute residuals and Table 2 versus actual
adapter output. Verify it only after the matching `check.py` report passes;
plotting alone does not establish correctness. It does not replace the Liang
flame comparison image.

`frozen.py INPUTS PROFILE.csv [--output NEW_DIRECTORY]` uses Python Cantera 3.2
and NumPy to reconstruct the pressure correction on eight frozen Case 4 faces.
It exports every ordered binary pair and its fraction of the mixture denominator
`Xj/Dij`, plus a JSON summary of low-Pr and Tr-clamped contributions. This is an
independent correlation replay, not a new C++ adapter sample or a flame solve.
Input profiles must have the exact 53-species order from `species.txt`. The report
records hashes, actual selected temperatures and all approximation limits.
It also reports the coefficient change when only the upper Tr clamp is removed.
That column is an explicitly unqualified extrapolation sensitivity; a large
clamped denominator fraction need not imply a large change in diffusivity.

## Additional species and measured high-pressure checks

`light_species.py INPUTS/ideal.yaml [--output NEW.json]` reads
`light-species-reference.json`. It compares author and stock GRI30 transport
without changing either input. Matsunaga's hydrogen measurements retain their
carrier direction, replicates and estimated 2% uncertainty (no confidence level
is supplied). The model is evaluated at the trace limit in the stated carrier;
the reverse-carrier result tests the composition-independent binary model.
The OH-air check retains the unknown exact air composition and reports the whole
N2/O2 bath range. It is exploratory, not an exact-composition acceptance test.
NIST temperature fits are evaluated only in their published ranges and remain
evaluated references, not newly obtained experimental points. Their uncertainty
ranges are reported without inventing a common confidence level.
Expected result: a reproducible report, including any failed property screens.
Exit 1 means at least one eligible hydrogen mean is outside the stated band.
No transport parameter, reaction or flame result is changed.

`self_diffusion.py INPUTS [--output NEW.json]` uses Dawson's pure-methane
self-diffusion measurements and the independently verified Takahashi Table 2.
It reports dilute and corrected predictions, the reduced states, and a
plus-one-atmosphere pressure-basis sensitivity. Points beyond the table range
are reported separately and do not count as in-range validation. Uncertainty
components are kept separate; there is no invented 95% acceptance band.
This is a property calculation, not a flame solve or a new C++ adapter probe.
Both scripts use the existing pinned Cantera 3.2 dependency and create no files
unless given a new output path. Run their plans before calculations and inspect
the source hashes and limits in the JSON reports.

`property_report.py LIGHT.json SELF.json EXISTING.pdf [--output NEW_DIRECTORY]`
adds two property-comparison pages to the existing verification PDF and exports
their PNG previews. It uses NumPy/Matplotlib and PyMuPDF, records input hashes,
and never edits the input PDF. Without output it prints its plan. Inspect both
new page renders and the combined page count before replacing the existing
report attachment. All new curves have explicit legends; this report does not
replace the separate Liang flame-speed comparison.
