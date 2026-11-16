# Psi-thermo tabulated-transport policy

`fgmDimixPolicy.H` validates opt-in omission of unused species diffusivities.
Inputs are immutable control, momentum, thermal-transport and combustion
dictionaries. Outputs are a suppression decision or an actionable failure.
All public internal, boundary and raw-mixture Dimix accessors still refuse
access when suppressed. This is not a species-transport approximation.

The supported laminar path is explicit Fourier. The RANS path is explicitly
declared kEpsilon with unity-Lewis eddyDiffusivity and Prt 0.7. It supports
steadyFlamelet, or fgmTable with strangFixedState integration. The latter needs
fresh full-versus-suppressed field/flux and timing qualification. Non-unity
Lewis, arbitrary turbulence and runtime-modifiable selection remain excluded.

The existing eddyDiffusivity::DEff returns alphaEff for every scalar; divj and
divq therefore use the same alphaEff rather than species Dimix. Suppression
changes neither those fluxes nor table chemistry. hePsiThermo and the SRK
mixture consume this policy; rebuild all affected concrete thermo instantiations
and relink executing app/probe products together. Do not infer live support
from a dictionary change or a new header beside an old binary.

There is no network or secret handling. Minimal input is `fgmSkipUnusedDimix yes`
with absoluteHa, immutable configuration and the explicitly supported models.
Verify exact library identities, original-zero matched physical field histories
and all three unexpected-Dimix negative controls. A transport parity result is
distinct from a paper comparison or scientific acceptance.
