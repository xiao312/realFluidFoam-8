# Optional unused diffusion calculation suppression

The full-fork `hePsiThermo` normally calculates every species mixture diffusivity
on every correction. The selected laminar Fourier model uses `alpha` for all
scalar diffusion and does not consume `Dimix`. The opt-in below suppresses only
that unused calculation. The SRK mixture also omits its unused diffusion-matrix
setup while preserving all active mixture reductions and corrected X/Y. Neither EOS,
enthalpy, heat capacity, Chung viscosity/conductivity or scalar transport.

Set `fgmSkipUnusedDimix yes;` in controlDict only with explicitly configured
`fgmEnergyForm absoluteEnthalpy; runTimeModifiable no;`, combustionModel
`fgmTable` or `steadyFlamelet`, thermo type `hePsiThermo`, momentum `simulationType laminar`, and thermophysical transport
`laminar { model Fourier; }`. Missing/incompatible selections fail during thermo
construction. This narrow initial qualification does not include turbulent or
finite-rate/species diffusion models. Without the switch, behavior is unchanged.

Fields and class layout remain unchanged. Both public Dimix accessors refuse
access while suppressed; no caller can silently consume the uncomputed fields.
The full policy is checked in the SRK mixture constructor before heThermo's
initial enthalpy query, and again before hePsiThermo calculation; subsequent
corrections read only the existing in-memory control flag. Dictionary reads are
unregistered to avoid collisions with later transport/combustion objects.
Runtime modification is refused so a process cannot turn the option off and
read stale fields between corrections. No credentials or external state are used.

Under this policy SRK cell/patch mixture queries retain all EOS/Chung coefficient
reductions and corrected mole/mass fractions. They omit TCMD/PCMD construction
and copying of four diffusion matrices. The light transport update clears those
matrices, and direct raw Chung/Takahashi Dimix access also fails before indexing.
The default complete update remains unchanged. No layout member or cache is added.
The constructor checks the concrete hePsi selection so unburnt/heRho paths cannot
accidentally skip data their raw diffusion calls still need. Enabled rereads fail.

The implementation depends on existing OpenFOAM mesh/time/dictionary APIs.
Its dependents are the registered compressibility-based thermo templates and
the explicit FGM diagnostic cases. Rebuild template registration libraries;
copying only a new solver cannot install this option.

Verification is a full-runtime baseline/opt-in comparison of cold pure O2, CH4
and mixed physical table states, including rho, Cp, h, T, mu, alpha and enthalpy
inversion, followed by identical fresh CFD cases and measured wall time. Invalid
transport and an attempted Dimix read must fail. See the dedicated validation
module for commands. A local syntax/source check is not runtime qualification.
# Explicit RANS diagnostic extension

`fgmRansUnityLeDiagnostic` adds only steadyFlamelet with RAS kEpsilon,
turbulence on, and eddyDiffusivity Prt0.7 to the unused-Dimix policy. The exact
eddyDiffusivity implementation uses thermo.alphaEff for Ha and species/Z;
alphaEff combines molecular thermal diffusivity with rho*nut/Prt and calls no
Dimix accessor. The default laminar policy and all raw/public Dimix refusal
guards remain unchanged. No class member or EOS/Chung calculation changes.
An explicitly requested but inconsistent RAS diagnostic fails before the first
property query. Exact-runtime property parity and fresh RAS CFD are still
required; this source inspection is not runtime qualification.
