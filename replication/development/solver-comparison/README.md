# Solver and chemistry comparison

This module investigates the low transient ideal-gas flame speed. It owns isolated
stock OF8 reactingFoam, DeepFlame OF7 dfLowMachFoam CPU/CVODE runs and native
chemistry probes. It does not change the production solver or accept a flame speed.

Inputs: the ideal-baseline phi110 seed, author GRI30/NASA7 inputs, verified Cantera
profile, pinned solver sources and environments. Outputs: separate cases, input
hashes, executable/link receipts, sampled profiles and chemistry CSV files.
Configuration: 100 atm, 298 K, phi=1.10, 4 mm / 8000 cells, central 0.2 mm HP
products slab, zero initial velocity, matching boundary conditions and 50 ns step
ceiling. End time 200 us is a comparison checkpoint, not a convergence criterion.

Dependencies: ideal-baseline and premixed-paper generators, OF8 pinned container,
SCNet OF7 installation, DeepFlame 7cb3294b275525cb8829ada3d3fbc067ab9323eb,
Cantera 2.6 native development library, Python and Slurm. Cantera 3.2 remains the
independent local reference. Downstream: flame comparison records and diagnosis.
All caches, HOME, builds and outputs stay inside the project. External OF7 is
read-only; credentials remain outside source. No DNN or GPU chemistry is enabled.

The stock case uses multiComponentMixture / sutherland / perfectGas / janaf,
standard chemistry and its native unity-Lewis transport. It is not a transport-
matched control. DeepFlame uses Cantera mixture-averaged transport. Neither full
flame comparison alone establishes a chemistry defect.

Chemistry checks compare instantaneous net molar rates and independent 50 ns
advances at identical flame states, then vary tolerances and interval. Report
OpenFOAM's concentration/temperature ODE, Cantera's physical CP reactor and
DeepFlame's isothermal CV reactor separately. Different reactor equations must
not be interpreted as an integrator error. Preserve failed build/run evidence.

Example: `python prepare.py plan stock CASE` is read-only; `apply` requires a new
case directory. `bash submit.sh plan ROOT RELEASE MODE` prints bounded Slurm
submission and placement; `apply` submits it. Modes select build/probe/flame jobs.
Verification: Python compilation without bytecode, bash syntax, git diff --check,
case input equality, scheduled startup, library dependency receipts and finite
fields. A chemistry discrepancy needs a reproducible state and tolerance study.

`chemistry-states.json` freezes eight sampled phi110 flame states, with the source
profile/mechanism hashes and any clipped negative roundoff recorded. `probe.sh`
builds the same executable separately against stock and qualified native libraries.
It records failed integrations without preventing the other cases from running.
Baseline SEULEX tolerances are 1e-8 absolute / 1e-6 relative; the qualified tighter
pair is 1e-12 / 1e-8. An earlier 1e-14 / 1e-10 attempt exceeded the stock step limit.

`cantera_probe.py PROFILE MECHANISM NEW_OUTPUT [--reference-pressure 100000]`
uses CVODE for physical adiabatic CP, isothermal CV, and the native concentration/
Cp-temperature ODE. The optional reference-pressure change is a diagnostic; it
does not replace the published Cantera flame curve. `analyze.py SNAPSHOT REFERENCE
OUTPUT_JSON --assert-cache-refresh` must fail on the unchanged native library:
its species enthalpy cache does not refresh after a 100 K temperature increment.
Source-vector comparisons normalize by the L1 norm of reference mass sources;
small net rates near equilibrium need separate interpretation.

DeepFlame dependency URLs and hashes are locked in `dependencies-lock.json`.
Packages are staged offline; the first cluster attempt failed because compute
nodes could not resolve the package host. Upstream CRLF shell files are normalized
in the private build copy. A small executable checks the converted mechanism with
native Cantera 2.6 before the flame run. Only YAML type names/default phase state
change for compatibility; NASA coefficients and reactions remain unchanged.

`sampleHistory.C` reuses the qualified flame-tracking core on stock/DeepFlame raw
line samples. Compile with `g++ -std=c++11 sampleHistory.C -o OUTPUT_BINARY`.
Run `OUTPUT_BINARY PROFILE_ROOT MANIFEST OUTPUT_CSV`; the manifest has time and
relative sample-directory columns in increasing time order. It expects the exact
`axisLine_T_rho_OH_p.xy` and `axisLine_U.xy` columns from prepare.py. This adapter
uses the existing 780.872245 K / OH=2e-5 markers and 5-us fit, not a new speed
definition. Raw files must be stable snapshots. Partial/mismatched rows fail.

Source packaging must preserve case. Export DeepFlame with `git archive REV`
from Git objects and extract on Linux; never copy a Windows working tree as build
input. Directory names can collide even when full file paths do not. Run
`python3 source_audit.py ARCHIVE LINUX_SOURCE_TREE` to verify every archived path
component and file against the build copy. Only documented CRLF normalization of
shell/configuration entry files is allowed. Output is JSON; mismatches return 1.
The audit is read-only and ignores added build products. Archive identity must
also match the recorded SHA256 and pinned Git revision.
