# Cantera property and chemistry bridge

This draft exposes the qualified `cantera-liang` models through a narrow C ABI
for later OpenFOAM experiments. It separates Cantera's C++ compiler ABI from
the OpenFOAM executable. It does not replace any active solver or turn a
FreeFlame profile into transient initial fields.

Inputs: a contained model-input directory (`ideal.yaml`, `srk.yaml`,
`species.txt`), stage1–5, explicit diagnostic options, temperature in K,
pressure in Pa and mass fractions in the exact declared species order.
Outputs: density kg/m3, absolute mixture enthalpy J/kg, Cp J/(kg K),
conductivity W/(m K), viscosity Pa s, molecular weight kg/kmol, partial specific
enthalpies J/kg, mixture diffusion coefficients m2/s and net species mass sources
kg/(m3 s). All are current-state evaluations. Absolute species enthalpies must
not be inserted into a sensible-enthalpy solver without its formation-enthalpy
transformation; no energy-source convention is silently selected here.

Configuration is explicit C function arguments, not environment-dependent model
selection. The header documents array lengths and ownership. Each MPI rank or
thread owns its own context; concurrent calls on one context are unsupported.
Errors return a code and message; C++ exceptions never cross the C boundary.
The evaluation call permits null partial-enthalpy and source buffers to skip
those calculations during a transport-only query. Mixture properties and
diffusion buffers remain required; omitted chemistry is not evaluated.
Inputs must be finite, sum(Y) within1e-8 of unity and Y>=-1e-9. Trace roundoff
within that bound is passed without normalization, preserving the queried state.

Dependencies: pinned Cantera3.2 SDK, C++17, and sibling `cantera-liang` adapters.
Potential dependent: a separate OpenFOAM property/chemistry experiment; no current
production solver depends on this bridge. The ABI itself has no OpenFOAM or
Cantera headers. The shared library and all dependencies must be pinned by hash.
No credentials are used. SDK and input references are read-only; build/cache/log
output stays below the explicitly supplied project root in scheduler jobs.

Example: `rf_ct_create(INPUTS, 3, "pressure-chemistry", error, sizeof(error))`,
then query species names, supply a matching mass-fraction vector, evaluate and
destroy the context. The shared library supports one model context per instance;
model selection never changes after initialization.

Verification: compile the shared library with the pinned SDK; compile `probe.cpp`
as an ABI0 client with no Cantera headers, load the library dynamically and compare
saved independent FreeFlame rho/h/Cp/conductivity values. Exercise invalid input
and species-count errors. Repeat the client inside the pinned OF8 container before
any CFD integration. This establishes linkage and property parity, not a flame.

`bash submit.sh plan ROOT RELEASE SDK INPUTS` prints the contained build and
qualification allocation; `apply` submits one core for at most20 minutes.
`probe.cpp` consumes the module's 100-atm profile schema. The initial job tests
ideal, smooth-SRK and bounded-diffusion contexts, including ABI0 caller/ABI1
library linkage, then repeats with the OF8 core library loaded in its container.
