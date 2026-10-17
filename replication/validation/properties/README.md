# Methane property probe

This utility loads the compiled `psiReactionThermo` runtime model and evaluates
225 methane states covering Figure 6. It writes `properties.csv` in its case
directory, with SI units and a recorded enthalpy-inversion error. It does not
implement a second EOS or substitute an external library for realFluidFoam.

Inputs: a one-cell generated case, pinned species coefficients, and the completed
solver build's headers/libraries through `LIB_rfFoam8_SRC` and `FOAM_USER_LIBBIN`.
The validation runner sets those paths and compiles the utility in its own job.
No credentials or network access are required. Outputs stay in that job's case.

Example after loading the isolated build environment: `wmake` then
`rfPropertyProbe -case CASE`. Expected result: 225 data rows, all positive/finite
bulk properties. The declared inversion criterion remains relative error below
1e-6. The probe records recovered temperatures, then restores the exact target
temperature for the property comparison. Exit 3 means a completed finite sweep
with one or more inversion criterion failures; other nonzero exits are errors.
The runner preserves both EOS sweeps and returns CHECK_FAILED/exit 3 if needed.
The comparison receipt counts those failures without hiding them or preventing
the independent property comparison. The CSV header states
units. Independent NIST comparisons are performed after execution; numerical
completion alone is not agreement with the reference model.

`compare.py SRK.csv PR.csv REFERENCE_DIR OUTPUT_DIR` verifies the pinned NIST
hashes and exact pressure/temperature coverage, then writes signed relative
errors and RMS/maximum absolute relative errors by pressure. It uses Python's
standard library. The output directory must be new. Enthalpy is excluded because
reference-state conventions differ. Cp is converted from J/(g K) to J/(kg K).
The comparison records input hashes and does not assign a scientific pass/fail
threshold. Plotting may consume the resulting CSV separately.

`plot.py COMPARISON_DIR --project-root ROOT` renders the verified comparison as
PNG and PDF with matplotlib; it keeps its cache under `ROOT/cache/matplotlib`.
Use the separately recorded analysis requirements to recreate that environment.
