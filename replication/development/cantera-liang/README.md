# Staged SRK flames in Cantera

This module runs Liang Figure 8(a) model stages with Cantera 3.2 FreeFlame.
It owns C++ thermodynamic and transport adapters. It does not claim to reproduce
unpublished PREMIX inputs or resolve the Figure 2 discrepancy.

Inputs: author GRI30 YAML, author species critical data, an ideal flame profile,
case number 1–5, and an explicit output directory. Pressure is 100 atm and
unburned temperature is 298 K. The article does not specify Tu numerically.
Outputs: solved profiles, speed versus refinement, property checks and callback counts.

Cases add SRK density, SRK calorics, Ely–Hanley conductivity, then Takahashi diffusion.
Default kinetics use physical concentrations and NASA reverse constants.
This preserves concentration-law chemistry; fugacity kinetics is a separate option.
SRK chemical potentials support equilibrium checks. Case 2 deliberately retains
ideal calorics and is not a consistent equilibrium model.
An ideal flame supplies a labelled steady-solver guess, not a transient restart.
No OpenFOAM run is resumed by this module.

Dependencies: pinned Cantera 3.2 C++ SDK, C++17 compiler, `ideal-baseline`, and
`liang-properties/ElyHanley.H`. The latter owns the molar reference-density mapping.
The author critical table approximates Liang's unprovided table.
NO, NO2 and N2O EOS coefficients are zero; transport parameters remain populated.
Original Soave alpha constants are explicit. No coefficient is fitted to flame speed.
Dependents: the Liang comparison report. Production OpenFOAM code does not depend on this module.

All generated state stays in the project directory. No secrets are used.
Linux SDK installation and compilation run in scheduler jobs. Preparation supports
`plan`; existing output paths fail. Source, SDK, input and executable hashes identify each run.

Example: `python prepare.py plan AUTHOR.yaml SPECIES_DICTIONARY PROFILE.csv OUTPUT`.
Use `apply` with the same paths to generate inputs. Then run
`liang-flame INPUTS CASE PHI OUTPUT`, where CASE is 1–5 and OUTPUT is new.

Verification: compile and run `test_srk.cpp`, then execute Case 1 parity and
frozen-state thermodynamic checks before interpreting nonideal flames. Require
Euler identities, pressure-root and finite-difference derivative checks.
Report grid/domain and initial-guess sensitivity separately from model activation.
Successful compilation is not scientific acceptance.
