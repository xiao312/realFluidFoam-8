# Optional unused diffusion calculation suppression

The full-fork `hePsiThermo` normally calculates every species mixture diffusivity
on every correction. The selected laminar Fourier model uses `alpha` for all
scalar diffusion and does not consume `Dimix`. The opt-in below suppresses only
that unused calculation. It changes neither mixture construction nor EOS,
enthalpy, heat capacity, Chung viscosity/conductivity or scalar transport.

Set `fgmSkipUnusedDimix yes;` in controlDict only with explicitly configured
`fgmEnergyForm absoluteEnthalpy; runTimeModifiable no;`, combustionModel
`fgmTable`, momentum `simulationType laminar`, and thermophysical transport
`laminar { model Fourier; }`. Missing/incompatible selections fail during thermo
construction. This narrow initial qualification does not include turbulent or
finite-rate/species diffusion models. Without the switch, behavior is unchanged.

Fields and class layout remain unchanged. Both public Dimix accessors refuse
access while suppressed; no caller can silently consume the uncomputed fields.
The policy is rechecked on correction, and dictionary reads are unregistered to
avoid collisions with subsequently constructed transport/combustion objects.
Runtime modification is refused so a process cannot turn the option off and
read stale fields between corrections. No credentials or external state are used.

The implementation depends on existing OpenFOAM mesh/time/dictionary APIs.
Its dependents are the registered compressibility-based thermo templates and
the explicit FGM diagnostic cases. Rebuild template registration libraries;
copying only a new solver cannot install this option.

Verification is a full-runtime baseline/opt-in comparison of cold pure O2, CH4
and mixed physical table states, including rho, Cp, h, T, mu, alpha and enthalpy
inversion, followed by identical fresh CFD cases and measured wall time. Invalid
transport and an attempted Dimix read must fail. See the dedicated validation
module for commands. A local syntax/source check is not runtime qualification.
