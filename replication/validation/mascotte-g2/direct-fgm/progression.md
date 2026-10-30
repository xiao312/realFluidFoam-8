# Next clean-start G2 diagnostics

The frozen f0d batch is a warm ideal-gas startup test on the registered 200622-cell
wedge. The following inputs are for subsequent source releases and fresh cases.
They do not modify that batch or qualify paper agreement. Continue useful
independent diagnostics when a physical discrepancy remains open; keep the
failed verdict and its provenance.

## Inlet and thermodynamic consistency

The measured mesh areas are 1.1155935404174525e-7 m² (oxygen) and
7.477962844114543e-7 m² (methane). Both give a wedge/full-annulus area ratio of
about 0.0138712672771. Thus the declared full-annulus flows 0.0444/0.1431 kg/s
become 0.0006158842671/0.0019849783474 kg/s respectively. This uses measured
face magnitudes, including the registered small CAD offset. Do not substitute
the nominal angle fraction or swap the two mass flows.

The inlet velocity is determined from this mass flow and the executing EOS
density. The serialized ideal velocity/rhoInlet is only an initial estimate;
the solver updates density and evaluates U before rebuilding phi. The inlet
pressure has zero gradient, outlet pressure is fixed to the table pressure,
and fixed inlet temperatures come from the exact table streams. Ha at a fixed-T
patch is recomputed with the executing local mixture and pressure. For the
absolute-energy mode, chemical heat release is diagnostic, not another source.

Check actual negative outward inlet phi against the specified inward flow.
The checker reports this and trapezoidal domain-mass/boundary-flux balance over
their common recorded interval. This is a useful diagnostic, not the exact FV
residual. A full open-domain energy balance additionally needs pressure work,
kinetic energy, convective enthalpy and diffusive heat flux at matching stages;
inlet flow agreement alone does not establish it.

Current pure-stream temperatures are warm. MASCOTTE requires O2=85 K and
CH4=288 K at the registered pressure. The mesh oxygen inlet diameter is 3.2 mm,
while the paper describes 3.6 mm upstream widening to 5 mm at injection. Keep
this geometry difference and raw mesh x coordinates visible. The apparent
injector exit near x=10 mm must be verified before shifting paper coordinates.

## Output configuration

Example `observations.json` for a separately admitted 0.1 ms fresh diagnostic:

```json
{
  "profileInterval_s": 0.000002,
  "fieldInterval_s": 0.000025,
  "averageStart_s": 0.00005,
  "radialPositions_m": [0.02, 0.03, 0.04, 0.06, 0.08],
  "imageGrid": { "axialPoints": 401, "radialPoints": 81 }
}
```

Use `prepare.mjs ... --end-time 0.0001 --observations observations.json` in the
read-only plan first. Profiles and image-plane samples are CSV with named
columns. Near-axis sampling is at r=0.1 mm, not the exact centerline. The image
plane is z=0; points outside fluid are omitted. Plot holes as holes, never
interpolate across the injector or walls. No mirror to a full cylindrical
cross-section should be implied without labelling the axisymmetric assumption.

`instantaneousProfiles` and `instantaneousImagePlane` contain the current
T/Z/c/OH and companion fields. `timeMeanProfiles`/`timeMeanImagePlane` use only
the actual OF8 mean fields. Averaging is disabled unless explicitly requested.
Retain `<time>/uniform/timeAverageProperties`; the checker reports the actual
per-field steps and accumulated time. In parallel the checker reads the
dictionary from every processor at that output time and requires identical
counters; reconstruction need not copy or rewrite the dictionaries.
An averaging window during ignition is a transient running average, not a
statistically converged flame. Mean and instantaneous panels need separate
titles, time/window labels, raw coordinate convention, table/source hashes and
the same consistent colour range for comparisons. The code never relabels an
instantaneous shot as the paper's mean.

The checker reports arithmetic RMS/max of T minus fgmTdiag. The table owns
composition/source; the executing thermo and transported Ha own temperature.
A substantial difference means the two-coordinate source table is being used
away from its original thermal manifold. It is not repaired by assigning table
temperature over the transported energy solution.

For field images, use the compact CSV plane on the native side for plotting,
or run OF8 `foamToVTK -case CASE -fields '(T Z c OH)' -latestTime` inside an
admitted postprocessing step. The latter exports full fields and requires a
qualified VTK/ParaView renderer. It is not a reason to transfer the mesh and
fields to ECS. Plot generation must preserve the source sampled CSV/VTK hash.

## Duration and parallel scaling

Run the repaired heating/contact/conversion and physical-table checks first.
Then qualify a short 4-rank G2 startup, keeping finite execution separate from
table-coverage/physical acceptance. After enough actual advancement, run:

```text
node forecast.mjs CASE --durations 0.0001,0.001 --ranks 4,16,32
```

This reads solver ClockTime over at most the last 100 completed intervals.
It excludes setup/cleanup/compilation; the 16/32-rank values are optimistic
perfect-scaling bounds until measured. The 200622-cell mesh gives about 50156,
12539 and 6269 cells/rank at 4/16/32 ranks. Memory must include the 53 species,
temporary thermo fields, matrix storage and per-rank copies of the table;
smaller cells/rank does not prove a small aggregate memory requirement.

Compare fresh equal-duration cases with decomposition choices:

```json
{ "method": "hierarchical", "n": [8, 2, 1], "order": "xyz" }
```

for 16 ranks, `[8,4,1]` for 32, or explicit `{"method":"scotch"}` if the
executing runtime provides scotch. The generator requires the product to equal
the admitted rank count and never splits the one-cell wedge direction.
`decomposePar` and parallel `checkMesh` must record actual cells per rank,
processor faces, imbalance and any empty partition. Keep the same actual
runtime-local MPI library qualification. The configurable batch manifest must
declare the same rank count as the actual Slurm allocation; its MPI reduction
and matched contact check verify that count before G2. The coordinator supplies
the new admitted resource profile.

Compare inlet phi, total mass, final temperature/progress ranges and profiles
between decompositions, recording numerical differences without expecting
bitwise identity from pressure reductions. First establish measured wall time,
peak memory and solver advancement; then choose the next fresh duration. The
50 mm and 200 mm inlet-convection scales in the input manifest are lower-order
flow scales, not relaxation or steady-state proof. A 20 us run cannot establish
flame length. An explicit-source CFL may be more restrictive than flow Co:
record rho, Sc and remaining raw-C coverage before increasing maxDeltaT. Do not
add clipping or alter chemistry merely to let a timestep cross a table bound.

## Switch to full PR/SRK

1. Retain the stock-thermo batch as a separate baseline. Build the new solver
   and `realFluidG2ThermoProbe` against one exact complete fork source/library
   stack. Inspect hashes and ldd; mixing stock thermophysical libraries with
   full-fork combustion/thermo headers is not a qualified transition.
2. Run pure O2/CH4 density, Cp/Cv, departure enthalpy and inversion probes at the
   declared pressures/temperatures. Qualify the fixed-T Ha pressure perturbation
   and incompatible-Ha negative control. Preserve NASA bounds and explicitly
   mark any 85 K polynomial extrapolation. PR and SRK are distinct choices;
   neither is the paper's volume-translated PRVTA.
3. Require a physical table with the matching 85/288 K streams and pressure,
   finite-rate chemistry/transport provenance, raw-C definition and useful
   cold mixing/ignition coverage. A warm table cannot be silently recast as
   cryogenic by changing only inlet T. A steady burning branch does not supply
   a missing unburnt state or uniquely resolve folded progress branches.
4. Prepare a fresh time-zero field from prescribed p/T/Y, copy the exact PR or
   SRK dictionary, then run `realFluidG2ThermoProbe -case NEW_CASE -initialize-Ha`
   using that exact full runtime. Retain hashes before/after. Ha includes EOS
   departure once; subtract only the same NASA formation enthalpy when deriving
   Hs. Never reuse ideal Ha or a previous CFD checkpoint. The runtime fixed-T
   boundary helper updates pressure-dependent departure during the solve.
5. Test a small closed/contact setup before bounded G2 mixing. Compare density
   after pressure correction with EOS density and increase outer-corrector
   counts as a measured sensitivity. The fork PengRobinson psi is rho/p,
   not the exact isothermal derivative of density. That is a reason to measure
   nonlinear closure, not evidence that every real-fluid diagnostic must stop.
   Record T−fgmTdiag and pressure departure from the fixed-pressure table. A
   two-coordinate ideal source table still lacks an enthalpy coordinate, so
   strong departures need a declared extended manifold or restricted use.
6. Replace the uniform reacted fill with a registered localized ignition recipe
   only when cold unburnt/mixing states are covered. This and a declared
   turbulence closure are necessary before interpreting G2 flame morphology.

Sources checked: OF8 [CSV sampled-set writer](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/fileFormats/sampledSetWriters/csv/csvSetWriter.C),
[lineUniform](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/sampling/sampledSet/lineUniform/lineUniform.C),
[unordered points](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/sampling/sampledSet/points/points.C),
[fieldAverage](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/functionObjects/field/fieldAverage/fieldAverage.C),
and [function-object time controls](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/OpenFOAM/db/functionObjects/timeControl/timeControlFunctionObject.C).
Runtime qualification remains required even when a dictionary matches upstream
source syntax.

The earlier frozen warm generator used the older `type uniform` sampling name.
The OF8 source registers `lineUniform`; this observation revision uses that
actual name and `type points; ordered no` for image-plane samples. This is a
case-output syntax correction, not a change to solver equations. Retain any
old batch failure; do not mutate its archived inputs to hide the difference.
