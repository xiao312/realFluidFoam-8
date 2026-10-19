# Chemistry settings and heat-release observation

19 October 2026. Scope: the phi=1.10 central-ignition comparison, including both
1800-K timestep variants, the 1400-K fresh kernel and the central products seed.
Runnable releases are a6d35b7 and 9a02703; their reacting binary SHA-256 is
687a2f1494346bdfe9e64f52fdc1fd8cf6569dd9528538850e5401d3d13b6d8a.
Library build 124657926 and the pinned OF8 environment remain common inputs.
Actual submitted dictionaries and startup selection logs were inspected; the
pending cooler case also derives from the same versioned generator.

## Active model chain

| Layer | Selection and meaning |
| --- | --- |
| Mechanism | Author's GRI30 input: 53 species, 325 reaction entries; no reduction or tabulation |
| Thermodynamics | hePsiThermo / SRKchungTakaMixture / soaveRedlichKwong / rfJanaf / sensibleEnthalpy |
| Chemistry model | `chemistryType { solver ode; method SRKchungTakaStandard; }`, chemistry on |
| ODE integrator | `seulex`, linearly implicit Euler extrapolation with adaptive step size and order |
| ODE tolerances | absTol=1e-8, relTol=1e-6, applied to the ODE concentration/T/p state vector |
| Initial chemistry step | initialChemicalTimeStep=1e-8 s; this initializes adaptive chemistry substeps, not the flow timestep |
| ODE defaults | maxSteps=10000, no explicit maxChemicalTimeStep cap, Treact default 0 K |
| Combustion closure | `combustionModel laminar`; integrateReactionRate defaults true, confirmed by the startup log |
| Momentum model | simulationType laminar, selected Stokes stress model |
| Turbulence–chemistry interaction | No PaSR, EDC, eddy-dissipation, presumed-PDF or flamelet closure is active |
| Transport | Chung–Takahashi; solver explicitly assembles molecular species diffusion and heat-diffusion terms. A laminar Fourier transport object is constructed, but its generic species/energy transport calls are commented out in these equations |
| Nitrogen | N2 is the transported mixture closure; the chemistry mechanism still contains N2 reactions |

The reaction input contains 268 reversible Arrhenius, 16 irreversible Arrhenius,
12 reversible third-body Arrhenius, 26 Troe falloff and 3 Lindemann falloff entries.
Its SHA-256 is c92d7b67c77faba2742de6999c990f383aea1413300706cee24bee0ada51ac40.
The real-fluid model name does not imply a turbulence closure or an equilibrium
chemistry solve. Cantera supplied only the versioned ideal-gas HP initial products
for one recipe; Cantera is not integrating any running case.

## Source sampling and solver sequence

The chemistry ODE state has 53 molar concentrations plus T and p. Its RHS fixes
dp/dt=0 within the local chemistry integration and computes dT/dt from species
enthalpies and heat capacities. The model provides its Jacobian to the stiff
integrator. Concentrations are initialized from runtime rho*Y/W, and negative
returned concentrations are clipped to zero by the ODE wrapper.

The laminar combustion corrector integrates each cell over the current flow
timestep. Its stored species source is

`RR_i = (c_i,end - c_i,start) * W_i / deltaT` [kg/m3/s].

The species equation uses those rates and corrected molecular diffusion. The
energy equation subsequently uses `reaction->Qdot()`. These cases use one outer
PIMPLE corrector and two pressure correctors: chemistry, species transport and
energy are segregated in this sequence. The end-step Eq.40 diagnostic separately
evaluates instantaneous chemistry and restores all stored integrated RR fields.
The observer therefore sees the source retained for the species/energy solve.

Chemistry step adaptation and Courant-controlled flow adaptation are separate.
The scalar absTol applies to ODE concentrations, T and p; it is not directly a
mass-fraction error bound. No reaction-rate integration setting or tolerance is
changed by adding heat-release observation.

## Heat-release definition and monitoring

The active custom chemistry implementation returns

`Qdot = -sum_i(Hf_i * RR_i)` [W/m3],

using species formation enthalpies and the stored rates. Positive values mean
net chemical heat release; negative values mean chemical heat absorption. This
quantity excludes heat conduction, species-enthalpy transport, pressure work and
kinetic-energy terms, so it is not a complete local energy balance.

The observer records extrema, peak location, signed integrated power, separate
positive/negative contributions, and left/right half-domain powers. Power per
cross-sectional area uses 1e-10 m2, the actual thin 1-D mesh area. Total power
includes both fronts. It also records Tmax and pressure bounds for alignment
with the flame-speed history. It calls Qdot() without solving chemistry again.

CSV sampling occurs every ten steps and at existing field writes; Qdot_used
fields are saved at the existing field-write cadence. Live attachment preserves
the original controlDict and records before/after hashes, library hash and
qualification job. No source history before attachment is inferred or invented.
See [observer module](../development/heat-release/README.md).

The initial observer qualification job 124866913 failed compilation after 30 s:
its Make options omitted the basic thermodynamics include directory required by
basicChemistryModel.H. No live case was modified. The next revision adds the
explicit thermodynamics include dependencies; a new qualification is required.

## Source evidence

- [Pinned custom chemistry model](https://github.com/xiao312/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/chemistryModel/chemistryModel/SRKchungTakaStandardChemistryModel/SRKchungTakaStandardChemistryModel.C): derivatives, Jacobian, integrated RR and Qdot.
- [Pinned ODE wrapper](https://github.com/xiao312/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/chemistryModel/chemistrySolver/ode/ode.C): concentration/T/p state and clipping.
- [Pinned seulex implementation](https://github.com/xiao312/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/ODE/ODESolvers/seulex/seulex.H): integrator family and order/step adaptation.
- Contained OF8 `src/combustionModels/laminar/laminar.C`: integrateReactionRate=true by default, solve(deltaT), direct RR source and Qdot accessor. This installed source and actual selection logs were read on SCNet.
- [Case generator](https://github.com/xiao312/realFluidFoam-8/blob/9a02703215334ddc4b9b4fa85dc6d6ea86eb6931/replication/validation/flames/generate_counterflow.py) and [premixed override](https://github.com/xiao312/realFluidFoam-8/blob/9a02703215334ddc4b9b4fa85dc6d6ea86eb6931/replication/development/premixed-paper/prepare.py): explicit input settings.
