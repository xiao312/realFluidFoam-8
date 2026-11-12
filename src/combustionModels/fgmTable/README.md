# FGM composition and source lookup

This module reads a declared table and supplies composition, raw progress
production and volumetric heat release to the solver. Thermodynamics owns
density, temperature and sensible energy. It does not generate flamelets,
submit runs or establish scientific acceptance. Inputs contain no credentials.

Version 1 (`forge-fgm-table-v1`) retains the existing mass-fraction or globally
normalized progress coordinate. Version 2 (`forge-fgm-table-v2`) transports the
physical mass-fraction sum C and normalizes only the lookup coordinate:

```
progress-coordinate mass-fraction-mapped
progress-species CO2 CO
c-min <one value per Z row>
c-max <one value per Z row>
c <strictly increasing eta values from 0 to 1>
```

For a lookup at Z, Cmin and Cmax are linearly interpolated in Z, then
eta=(C-Cmin)/(Cmax-Cmin). Sc remains the raw volumetric C source in kg/m3/s;
there is no rho multiplier and no normalized-coordinate transport equation.
Every node must satisfy sum(Y of progress-species)=Cmin+eta*(Cmax-Cmin) to
1e-8 absolute. Zero-span rows must contain the same state at every eta.
Only C=Cmin is admissible when the interpolated span is zero.

The table's `Q` must match the solver energy convention. For the current
sensible-enthalpy equation that is formation-enthalpy heat release at the
thermo reference state, not Cantera's separate current-temperature total heat
release. Full species thermodynamics must match the physical table mechanism.

`boundsPolicy error` is the default. Explicit `clamp` is a diagnostic choice:
it limits lookup coordinates only, never modifies transported C or Z, and logs
cumulative counts and maximum raw-C/Z excursions. Clipping is evidence to
review, not a scientific pass. Species sums or malformed tables remain fatal
under either policy. Written source fields and species boundary conditions are
refreshed by the model; fixed species inlet data remain owned by the case.

Relative table names first resolve through `Time::path()/caseConstant()`.
In OF8 a processor case's `caseConstant()` is `../constant`, so every rank
reads the same case-owned input instead of searching only processorN/constant.
This follows the upstream TimePaths API. An explicit absolute table path is
also supported. The validation batch binds that absolute case-owned path and
its hash before decomposition, permitting existing frozen libraries to execute
without copying the large table once per rank. Neither path uses a donor CFD
state or changes table bytes. Actual serial/MPI parity remains required.

Build as part of `src/combustionModels` in the qualified OF8 environment.
Dependencies: OpenFOAM field/dictionary types and the fork's combustion base
interface. Dependents: `reactingFoamSolveZ`, table/field probes and validation
cases. Example: the `fgmTableCoeffs` dictionary selects a table file and
`boundsPolicy error`. Verify v1 fixtures with the retained table probe, then v2
mapping/zero-span/refusal cases and an actual clean-start physical table run.
Compilation and synthetic lookup checks alone do not qualify combustion.

## Optional fixed-state source integration

The reader's `advanceSource(Z,rho,C,dt)` integrates its piecewise-linear raw-C
source exactly while Z and density remain fixed. `sourceCurve` exposes the same
interpolated C/source arrays for independent allocated probes. Both require a
v2 mass-fraction-mapped table. The scalar kernel is copied unchanged from
`direct-flamelet/source_ode.hpp` at `c67dfe2910dc2275270d3dccc2a5f3fedb75862a`.
Its local name is `fgmSourceOde.H`, which OF8's include-directory generator finds.
It introduces only C++ standard-library dependencies.

`fgmTable::advanceProgressSource` applies that kernel to explicit input fields
and returns a new internal scalar field. It does not modify the input fields,
oldTime storage, species, temperature or energy. It reports stage duration,
segment crossings and integrated progress change. An outward domain event is
fatal, including its cell, state and elapsed time; no source is zeroed or clipped.
This refusal applies even when ordinary lookup uses `boundsPolicy clamp`.
Zero-span pure-stream rows can remain fixed only with exactly zero source.

The optional solver coupling is documented in the solver README and
`replication/validation/fgm-source-split/README.md`. The default explicit source
path is unchanged. The source table still describes its generating ideal-gas
flamelets; coupling it to SRK/PR does not establish matching chemistry or thermal
states. Source integration cannot repair this model discrepancy.

## Version3 weighted progress

The optional `forge-fgm-table-v3` schema declares
`progress-coordinate weighted-mass-fraction-mapped` and `progress-weights`, one
finite positive dimensionless weight per progress species. It transports
C=sum(weight_i*Yi), with raw volumetric source sum(weight_i*omega_i) inkg/m3/s.
Maders uses weight_i=MW_H2O/MWi forCO2,H2O,H2, so C=MW_H2O*gamma. This constant
scaling preserves the published transport equation and source, without changing
its physical units in the solver. V1/v2 semantics remain unchanged; weights in
older schemas are refused. Weighted C may exceed1; its physical upper bound is
the largest declared weight, not1. Each node must still reconstruct the declared
weighted coordinate from its species. No source clipping or species renormalization.

Verification: compile the reader and query real DRM19-derived weighted states;
compare C and signed sources independently. Exercise wrong weights and missing
weights as refusal controls. Run legacyv2 probe unchanged. Build and physical CFD
remain separate; no weighted coflow qualification is established by this change.
