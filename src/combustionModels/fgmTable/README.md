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

Build as part of `src/combustionModels` in the qualified OF8 environment.
Dependencies: OpenFOAM field/dictionary types and the fork's combustion base
interface. Dependents: `reactingFoamSolveZ`, table/field probes and validation
cases. Example: the `fgmTableCoeffs` dictionary selects a table file and
`boundsPolicy error`. Verify v1 fixtures with the retained table probe, then v2
mapping/zero-span/refusal cases and an actual clean-start physical table run.
Compilation and synthetic lookup checks alone do not qualify combustion.
