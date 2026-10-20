# Liang property models and Figures 1–2

This module tests SRK density, fixed-composition SRK critical points, and
Ely–Hanley conductivity before these closures enter reacting calculations.
It does not establish agreement of staged flame speeds or reproduce the
unspecified rich-hydrogen conductivity modification in Liang's paper.

Inputs are the pinned author GRI species dictionary, compiled OF8 library,
an exact source release, and the locally held Liang PDF. The probe calls the
library's `soaveRedlichKwong<rfSpecie>` density and coefficient methods.
Mixture coefficients are explicitly assembled with the library's geometric
mixing rule; the critical-point calculation is a fixed-composition inflection,
not a full multicomponent phase-stability calculation.

`ElyHanley.H` is a reusable C++11 conductivity kernel. Its species inputs are
Tc [K], Pc [Pa], Vc [m3/kmol], W [kg/kmol], omega, and ideal Cp/R. It takes
mole fractions, partial molar volumes [m3/kmol], mixture molar volume, and T.
It returns W/(m K). It neither selects an EOS nor changes viscosity/diffusion.
The reference density uses methane's mass per corresponding molar volume.
All inputs must be finite; nonpositive shape factors or mixture volume fail.
Partial molar volumes can be negative. The shape correlation bounds their
reduced values to [0.5,2], as it does for other out-of-range values.
The author NASA fits undershoot Cp/R=2.5: atomic H by about 1.2e-8 and atomic N
by 0.00136233 near 2115 K. A 1-K audit over 200–3500 K found these minima.
Undershoots below 0.002 give zero internal conductivity; larger violations fail.
This transport-only correction leaves thermodynamic Cp, enthalpy and kinetics unchanged.

The explicit `massDensityShortcut` mapping is a diagnostic variant only. It
reproduces the omitted molecular-weight factor in the Cantera 3.2 formula,
using our own kernel and the same SRK state. It does not run a Cantera flame
or establish the unprovided Liang implementation. Both curves remain labelled.

The oxygen sweep uses its NASA polynomial directly. Values below its stated
200 K bound are explicitly marked extrapolated; no temperature clipping or
caloric inversion is used. These values are exploratory, not qualified calorics.

Outputs are CSV sweeps, derivative residuals, input/product hashes, NIST
snapshots and local PDF/PNG comparisons. Raw data and copyrighted paper crops
stay outside Git. No credentials or network are needed by the compiled probe.
The optional NIST fetcher uses public HTTPS and records its full query/hash.

Dependencies: qualified realFluidFoam headers/libraries, OF8 wmake, C++11,
Python standard library; plotting additionally uses PyMuPDF. Dependents are
the staged-model development and project comparison report. The kernel can
be included by a future solver adapter without a Cantera runtime dependency.

Example inside the qualified container:
`wmake PROBE_DIR && rfLiangPropertyProbe SPECIES_DICTIONARY OUTPUT_DIR`.
The output directory must exist and be empty. Compile and run only in a
scheduler job. `submit.sh plan ROOT IMAGE RELEASE` is read-only; `apply`
submits the bounded property job.

Verification: `python3 -B check.py OUTPUT_DIR`, `git diff --check`, and
`bash -n run.sh submit.sh`. Expected: finite positive property values, normalized
critical derivative residuals below 1e-10, pure-fluid critical recovery within
the truncation error of upstream SRK constants, and recorded extrapolation.
Reference disagreement is reported separately from implementation checks.
The Figure 1 renderer uses `figure1-calibration.json`, measured from the original
embedded raster. It records the calibration hash with the artifact. Its line and
triangle readings remain distinct comparison targets; agreement with one does
not imply agreement with the other. `python -B test_plot_geometry.py` checks
the original axis ticks against the retained source-pixel positions.

## Independent critical-point audit

`critical_audit.py` checks Figure 2 without loading an OpenFOAM library. It reads
the same species dictionary and the native probe CSV, then compares a numerical
pressure-inflection solution with a separately calculated SRK solution. It also
reads the local PDF vector curves and tests their implied mixture covolume.
Inputs: `--species DICTIONARY --native critical.csv --paper PAPER.pdf`.
Output: `--output NEW_DIRECTORY`, containing JSON and CSV evidence. `plan` reads
inputs and reports paths; `apply` writes a new directory. Existing output fails.
The audit needs NumPy and PyMuPDF. It has no network, credentials, scheduler,
chemistry, or solver-state dependency. It does not fit or change physical data.

Example: `python -B critical_audit.py plan --species INPUT --native CSV
--paper PDF --output OUTPUT`. Run `apply` with the same arguments after discovery.
Verification: `python -B test_critical.py` and the audit `apply` command. Expected:
independent solutions agree with the native probe; publication disagreement is
reported separately. `--require-paper-match` makes publication disagreement fail
explicitly, so the original symptom remains reproducible.
`critical_math.py` owns the independent SI equations and numerical derivatives.
`critical_plot.py plan|apply AUDIT_JSON NEW_PNG` uses Matplotlib to visualize
the covolume consistency check. It is a diagnostic plot, not a Figure 2 replica.

See `NOTICE` for equation/code-reference attribution. No nonideal Cantera flame
results are generated by this module.

## Conductivity mapping diagnostic

`conductivity_probe.py plan|apply INPUTS NEW_OUTPUT [--profile PROFILE_CSV]`
compares the current explicit partial-volume map with the coupled component
map and fixed-volume noncorrespondence correction documented in NBS TN 1039.
`conductivity_math.py` owns the independent NumPy equations. The prescribed
mixture volume still comes from SRK; this hybrid is not the full TRAPP program,
which also uses a methane reference EOS. Both the current and original reference
constant sets remain explicitly named. No coefficients are fitted.

Inputs are a Cantera 3.2 `ideal.yaml`, matching `species.txt`, and optionally a
saved profile with named mass-fraction columns. Outputs are a new CSV/JSON
directory containing component maps, conductivity contributions, derivative
checks and input hashes. Dependencies are NumPy and Cantera 3.2; the probe has
no network, secrets, scheduler or flame-solve dependency. It does not change
the C++ kernel. Verification checks pure-fluid recovery of the coupled map,
fixed-volume derivative step sensitivity, and parity with saved baseline
conductivity where a matching profile is supplied. Property or paper agreement
is reported separately from those implementation checks.
`--pure-species O2` replaces the fresh-H2 sampling with pure oxygen at 100 atm,
200–1000 K in 5 K increments, for an independently labelled Figure 1 comparison.
It cannot be combined with `--profile`. The input mechanism still determines
the ideal Cp and dilute conductivity; its identity must not be conflated with
the earlier native-library input. Sub-200 K caloric extrapolation is excluded.
