# rfReactingFoam

Our independently named development target starts from
`applications/solvers/realFluidReactingFoam` at upstream
48506de20ce67f35279c5347b09dcd86865a4c39. Initially only the build target/name
changes; equations, PIMPLE placement and library calls are identical. Original
GPL notices are retained. This does not fix known thermodynamic/chemistry issues.

Inputs: OF8 case and realFluidFoam headers/libraries. Configuration remains
controlDict/fvSolution/thermophysicalProperties/chemistryProperties. Outputs:
standard OpenFOAM fields/logs from `rfReactingFoam`. Dependencies: qualified OF8
runtime and pinned library build. Dependent: development benchmark runner.
No credentials or network access.

Build in an isolated scheduler job. Set `LIB_rfFoam8_SRC` and `FOAM_USER_LIBBIN`
to the selected library build and `FOAM_USER_APPBIN` to the new job's bin, then
run `wmake SOLVER_COPY`. Never build into a live job. Verify SHA-256 and ldd;
compare endpoint field bodies against the original executable on identical input.

