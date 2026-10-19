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

Cases 1 and 3–5 also calculate HP equilibrium with VCS, checking enthalpy and
element conservation. This diagnostic uses SRK fugacity for the nonideal cases;
it remains distinct from the concentration-law flame kinetics. It does not
replace the saved ideal-profile numerical guess. Equilibrium and flame endpoints
can differ when their chemical equilibrium conventions differ.

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

`python check.py RESULT [--ideal-reference-cm-s 7.467003112153642]` reads completed
qualification output. Gates: ideal parity within 0.1%, last grid change below 0.3%,
mass-flux relative range below 0.1%, and species-sum error below 1e-7. These
are numerical screening limits, not evidence of publication agreement.

FreeFlame Newton iterates can contain small negative species fractions. The
conductivity adapter projects its transport-only composition to nonnegative,
normalized fractions and recalculates matching SRK volumes. It does not change
the thermo state or solution fields. Final profiles must have Y >= -1e-9.
The callback report counts these projections and negative partial-volume states.

`prepare_sweep.py plan|apply MECHANISM SPECIES OUTPUT PROFILE_DIR...` prepares
the declared 12-condition phi=0.92–1.44 sweep. Earlier directories win exact
profile ties; the nearest saved phi supplies a numerical guess when necessary.
`plan.json` records target phi and guess phi separately. The inlet uses target phi.
Each stage uses `submit.sh plan|apply ROOT RELEASE SDK INPUTS STAGE BUILD PHI`.
