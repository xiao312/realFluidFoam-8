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

`prepare.py INPUTS [--output NEW.csv]` plans/generates 756 prescribed states
for CH4-N2, H2-N2 and trace OH-N2. `property_probe.cpp` evaluates the actual
adapter and `check.py REQUESTS.csv SAMPLES.csv` checks factors to 1e-10 relative,
symmetry to 1e-12, and mixture reconstruction to 1e-7. The latter limit accounts
for subtractive cancellation in the near-pure bath; the existing ordinary flame
state reconstruction retains its 1e-10 limit. The probe also reports actual Pr/Tr
so floating-point crossings of the discontinuous Pr=0.1 policy are explicit.
Prescribed correlation states can extend below a mechanism's fitted temperature
range; their dimensional dilute coefficients are not accepted property predictions.

Run `bash job.sh plan ROOT RELEASE SDK INPUTS`, then submit `job.sh apply` with
those same inputs to Slurm (one CPU, ten-minute cap, explicit project log paths).
Expected: `corrected-report.json` passes and `legacy-report.json` fails when the
published Pr=3 correction is deliberately disabled. Preserve both reports.

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
Run `git diff --check`. For the C++ probe use `job.sh plan` before scheduler
submission; its documented positional inputs are ROOT RELEASE SDK INPUTS.
The probe never solves a flame or changes an input file.
