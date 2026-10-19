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

The experimental `rf_ct_advance_cp` call integrates a closed, adiabatic,
constant-pressure homogeneous reactor with Cantera CVODES. Its independent
variables are mass, total enthalpy and species mass fractions for nonideal models.
Stage 1 uses Cantera's equivalent ideal-gas temperature formulation to avoid
repeated HP inversions; the independent Python reference retains total enthalpy.
Each call resets
the supplied TPY state and time to zero; it never continues another cell's ODE
history. A context reuses the reactor and integrator allocation, with explicit
reinitialization. Inputs add duration (s), relative tolerance and absolute
tolerance. Outputs are final T (K) and Y. The call does not choose a CFD energy
source or return an ambiguously normalized integrated source.

This closure is distinct from the native solver's concentration ODE and from
DeepFlame's isothermal integration. It is not a test of the ODE integrator alone.
For nonideal stages with departure calorics, `smoothed-alpha` is required because
the original high-temperature alpha extension has enthalpy jumps. No active CFD
solver calls this function yet. On integration failure, the context discards its
reactor state; the next call starts independently.

Qualification uses frozen ideal-flame states and independent Python Cantera3.2
`ConstPressureReactor` calculations at 50 ns, 500 ns and 5 us. Compare T, every Y,
mass and elemental conservation, and specific enthalpy. Repeat states in reversed
order to detect history leakage. Nonideal tests establish conservation only;
they do not independently validate the custom thermodynamic closure.

Prepare references with `python reactor_reference.py plan|apply IDEAL_YAML
PROFILE NEW_JSON` using the pinned Python Cantera environment. Submit the C ABI
test with `bash reactor-submit.sh plan|apply ROOT RELEASE SDK BUILD INPUTS
REFERENCE`. It verifies the built library hash and records each result and input
hash; the test script itself imports no Cantera package. The expected result is
ideal-reference parity, conservation for both models and order-independent calls.
