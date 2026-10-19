# Cantera extension for Liang Figure 8(a)

19 October 2026. Status: adapters compiled and executed in FreeFlame. Cases 1–4
have passed numerical screening at phi=1.10; Case 5 qualification is running.
See the [implementation results](cantera-liang-results-20261019.md) for job and
source identities. This audit explains the design, not scientific acceptance.
The owner's latest
instruction supersedes the earlier restriction to ideal-gas Cantera calculations.
The target is all five cumulative model cases, with GRI30 held fixed.

## Decision

A standalone C++ application linked against Cantera 3.2 can register project-owned
thermodynamic and transport classes and run the existing freely propagating flame
solver. A complete Cantera or Python-binding rebuild is not required by the API.
`Factory<T>::reg` is public, and both `ThermoFactory` and `TransportFactory`
inherit that interface. Registration must happen before `newSolution` loads the
phase. The subsequent C++ SDK builds and flame runs verified this route.
See [FactoryBase.h](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/base/FactoryBase.h),
[ThermoFactory.h](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/thermo/ThermoFactory.h)
and [TransportFactory.h](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/transport/TransportFactory.h).

Use Cantera v3.2.0, commit `4a8358eb80cfeb50474386b5f9ec0b3a83519889`.
The existing operator source copy is `state/cantera-v3.2.0`; additional inspected
official source files are under `state/cantera-liang-20261019`. Keep SDK,
compiler, dependency versions and executable hashes in the resulting build
manifest. Do not mix the existing Cantera 2.6 DeepFlame SDK with this adapter.

The official [C++ flame-speed example](https://github.com/Cantera/cantera/blob/v3.2.0/samples/cxx/flamespeed/flamespeed.cpp)
already constructs `newSolution`, `newDomain<Flow1D>("gas-flow", sol)`, calls
`setFreeFlow`, assembles inlet/flow/outlet into `Sim1D`, sets a fixed temperature
location, enables energy, solves and extracts inlet velocity. Adapt that example
rather than constructing a replacement flame solver.

## What reaches the flame equations

At each grid point, `Flow1D::updateThermo` sets temperature, composition and
pressure, then obtains density, molecular weight, mass heat capacity, partial
molar enthalpies and chemical production rates. Therefore registered property
overrides actually enter continuity, species and energy residuals. Transport is
evaluated at grid midpoints through `thermalConductivity` and mixture diffusion
methods. These are runtime calls, not values captured only in the initial guess.
See [Flow1D.h, updateThermo](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/oneD/Flow1D.h#L511)
and [Flow1D.cpp, updateTransport](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L419).

Cantera 3.2 differentiates the **full partial molar enthalpy profiles** in the
species enthalpy diffusion term. Its temperature equation uses mixture `cp`,
reaction production rates multiplied by partial molar enthalpies, and diffusive
fluxes multiplied by their spatial gradients. It does not merely substitute
ideal species `cp * grad(T)` for that last term. See
[evalEnergy](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L704)
and [grad_hk](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L1344).

At constant pressure, the thermodynamic identity
`dh = cp dT + sum(hbar_k/W_k dY_k)` uses **partial molar** enthalpies.
Combining that identity with species conservation gives the structure above.
Thus a consistent nonideal phase can be used without replacing the energy
equation solely because Liang solves total enthalpy. This is an analytic
inference from the implemented residual; discrete total-energy conservation and
grid convergence still require measurement. Pure-species enthalpies at the
mixture pressure are not interchangeable with partial molar enthalpies.

## Five cases and the needed separation

The cumulative interpretation follows the supplied Liang paper and the existing
[paper audit](liang-2019-premixed-audit.md). Missing author parameter tables and
transport details still limit an exact reproduction.

| Case | Density | Caloric properties | Conductivity | Diffusion |
|---|---|---|---|---|
| 1 | Ideal gas | NASA ideal mixture | Existing ideal baseline | Existing mixture-averaged baseline |
| 2 | SRK | Ideal, deliberately retained | Baseline | Baseline |
| 3 | SRK | Consistent SRK departures and partial molar enthalpies | Baseline | Baseline |
| 4 | SRK | Same as Case 3 | Ely–Hanley | Baseline |
| 5 | SRK | Same as Case 3 | Ely–Hanley | Takahashi-corrected mixture average |

Case 2 is an intentional model ablation, not a fully consistent thermodynamic
phase. Record that explicitly. Case 3 adds caloric effects; it must not silently
change reaction mass-action conventions as a side effect.

The built-in `high-pressure` transport model already contains Ely–Hanley,
Takahashi and Lucas viscosity. Switching directly from `mixture-averaged` to
`high-pressure` combines changes that must remain separated here. Its constructor
is protected, but a public project subclass can invoke it. Its critical property
vectors and correction matrix are protected and accessible to that subclass.
See [HighPressureGasTransport.h](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/transport/HighPressureGasTransport.h)
and [TransportFactory.cpp](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/TransportFactory.cpp).

## Thermodynamic implementation boundary

There is no registered SRK phase in the audited factory. The built-in
Redlich–Kwong model is not SRK: it divides its attraction coefficient by
`sqrt(T)` and supports a linear temperature parameterization for that coefficient.
Several internal derivative helpers are not virtual. Overriding only its mixing
expression therefore leaves inconsistent derivative paths. Peng–Robinson has a
different attraction denominator. Neither is an exact SRK replacement selected
by changing its name or critical coefficients. See
[ThermoFactory.cpp](https://github.com/Cantera/cantera/blob/v3.2.0/src/thermo/ThermoFactory.cpp),
[RedlichKwongMFTP.h](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/thermo/RedlichKwongMFTP.h)
and [PengRobinson.cpp](https://github.com/Cantera/cantera/blob/v3.2.0/src/thermo/PengRobinson.cpp).

For the smallest isolated adapter, derive from `IdealGasPhase` to reuse species
loading and NASA reference states, but own the complete SRK property contract.
`pressure()` and `setPressure()` are virtual; set density through the base state
storage after selecting the gas root. Inherited physical concentrations then
use the changed density. For the caloric stages, implement mixture enthalpy,
heat capacity and partial molar enthalpies consistently. Supply partial molar
volumes for Ely–Hanley. Explicitly reject unsupported state setters or implement
them; inherited ideal `setState_DP`, internal energy, compressibility and related
methods must not quietly masquerade as SRK. See
[IdealGasPhase.h](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/thermo/IdealGasPhase.h).

For the selected SRK convention:

```
p = R T/(v-b) - a/[v(v+b)]
a = sum_i sum_j X_i X_j sqrt(a_i a_j)
b = sum_i X_i b_i
h_departure = p v - R T + (T da/dT - a)/b * log(1+b/v)
```

Use one shared coefficient kernel for density, departures and derivatives.
Handle zero-attraction/covolume limits analytically. Do not infer zero transport
critical properties from the paper's neglect of NOx EOS coefficients. Partial
molar enthalpy must satisfy `sum(X_k hbar_k) = h_molar`; `cp` must match the
constant-pressure derivative of mixture enthalpy. Finite differences are useful
independent tests, but a noisy nested numerical derivative inside every flame
Jacobian evaluation can spoil convergence. The existing native SRK kernel and
Figure 1/2 probes supply independent comparison data; Figure 2 agreement with
Liang remains unresolved and is not a fitting target for this extension.

### Equilibrium and kinetics are distinct contracts

`BulkKinetics` multiplies forward and reverse mass-action products by
**activity concentrations**, while third-body concentrations use **physical
concentrations**. Reverse equilibrium factors use standard chemical potentials
and standard concentration. An EOS replacement can therefore alter rates beyond
the intended density change. See
[BulkKinetics::updateROP](https://github.com/Cantera/cantera/blob/v3.2.0/src/kinetics/BulkKinetics.cpp#L448).

The ideal phase returns physical concentrations as activity concentrations.
The cubic mixture-fugacity base returns `phi_k X_k p/(R T)` instead. These differ
from `X_k/v`. A stock cubic phase is consequently not a neutral test of density
alone. See [IdealGasPhase.h](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/thermo/IdealGasPhase.h#L441)
and [MixtureFugacityTP.cpp](https://github.com/Cantera/cantera/blob/v3.2.0/src/thermo/MixtureFugacityTP.cpp#L261).

Keep an explicit kinetic-closure setting. The direct concentration-law
comparison retains NASA reverse constants and uses the SRK physical
concentrations, matching the intended unchanged-mechanism experiment. A
thermodynamically consistent fugacity-law variant is a separately named
sensitivity, unless independent evidence establishes Liang's choice. The
supplied main paper does not resolve this implementation detail.

Overriding `h`, `cp` and density on an ideal phase is **not sufficient** to call
its `equilibrate("HP")` result SRK equilibrium. The remaining ideal chemical
potentials, activity coefficients and `isIdeal()` flag would still drive an
ideal chemical equilibrium calculation. A fully thermodynamic SRK equilibrium
adapter also needs fugacity, entropy, chemical potentials and consistent
derivatives. Cantera's equilibrium implementation consults the phase's ideality
flag; see [vcs_VolPhase.cpp](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/vcs_VolPhase.cpp).
If concentration-law kinetics is retained independently of fugacity equilibrium,
the two stationary compositions need not agree; report both rather than using
one to certify the other.

## Transport adapter

Derive a staged class from `HighPressureGasTransport`, retain baseline viscosity,
and dispatch conductivity to the baseline for Cases 1–3 and Ely–Hanley for
Cases 4–5. Dispatch all requested mixture and binary diffusion methods to the
baseline through Case 4 and the Takahashi path for Case 5. Configure Soret off
for this first comparison and record the mixture-gradient basis. `Flow1D`
recognizes the multicomponent paths by specific model strings; a uniquely named
custom model follows its mixture path. Check both `getMixDiffCoeffs` and
`getMixDiffCoeffsMass`, rather than implementing an unused variant. See
[Flow1D.cpp](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp).

The stock high-pressure initializer queries pure-species critical properties
from the thermodynamic phase. This conflicts with deliberately zeroed NOx EOS
parameters and absent radical data. An adapter can call `MixTransport::init`,
populate its protected critical-property vectors from an explicit transport
table and resize its correction matrix. Fail on missing properties; do not
silently take unrelated database defaults. See
[HighPressureGasTransport.cpp](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/HighPressureGasTransport.cpp#L129).

Cantera 3.2's Ely–Hanley implementation maps reference density as
`rho_mix * h_mix`; the existing project kernel also exposes a molar-consistent
mapping using methane molecular weight. Preserve the distinction in the run
configuration and output. Use the project's qualified kernel for the declared
primary mapping, and retain the stock mapping as a labelled sensitivity. A
visually closer property curve does not establish the author's implementation.
See [the actual mapping](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/HighPressureGasTransport.cpp#L438)
and [the local property module](../development/liang-properties/README.md).

## Initialization and qualification sequence

Cantera's default free-flame initializer uses HP equilibrium to construct an
initial temperature/composition profile. That is an initial guess, not a
prescribed equilibrium profile throughout the converged flame. Its free-flame
solution determines velocity, temperature and composition from the residuals.
See [FreeFlame.set_initial_guess](https://github.com/Cantera/cantera/blob/v3.2.0/interfaces/cython/cantera/onedim.py#L636)
and the [C++ example](https://github.com/Cantera/cantera/blob/v3.2.0/samples/cxx/flamespeed/flamespeed.cpp).
It follows that changing the initial equilibrium seed should be tested by
independent converged solutions, not assumed to explain a permanent speed error.
Transient OpenFOAM initialization can still affect the duration and trajectory
of ignition; that is a separate question.

1. Compile the SDK executable and reproduce the saved Case 1 at phi=1.10,
   100 atm and 298 K, with the same mechanism and transport conventions.
2. Test property derivatives, mixture identities, ideal limits, SRK pressure-root
   residuals, concentration-law rates and transport stages on frozen flame states.
   Add call counters or exported node properties proving the selected callbacks
   are used during the actual residual evaluation.
3. Run Cases 2–5 at phi=1.10 first, preserving each model's original input and
   numerical settings. Export `rho, h, cp, hbar, lambda, D, wdot` on the solved
   grid alongside speed, mass flux and total enthalpy flux residuals.
4. Solve from two independently constructed initial profiles. An ideal-HP seed
   is permissible as a labelled numerical guess while real-fluid equilibrium is
   being implemented; it must not be presented as real-fluid equilibrium data.
5. Require grid/domain convergence and model-activation checks before sweeping
   equivalence ratio. Keep every failure, mapping variant and unresolved model
   choice in the result manifest. Do not tune EOS constants to flame speeds.

This audit establishes a feasible software path and identifies the properties
that must be consistent. It does not establish an exact replication of Liang's
unpublished modified PREMIX implementation or guarantee that all five curves
will match the figure.
