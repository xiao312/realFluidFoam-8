# Passive composition control for cold G2 mixing

This module creates a separate, nonreacting composition table to compare the
absolute-Ha/transported-Z pathway with a direct-species sensible-h cold control.
It is an analytic diagnostic, not a flamelet solution, paper validation target,
chemical fit, or replacement for a failed physical profile.

Inputs are an unchanged, verified steady-table directory and its exact phase
metadata. The existing strict loader verifies that original input. The new table
copies only its format/condition/element-coefficient header and creates two pure
endpoints: Y_CH4=Z, Y_O2=1-Z, all other species and chemical sources zero.
Linear interpolation is exact for this composition law. The copied chi label is
inactive in this passive lookup; it is not a physical dissipation calculation.
The interpolated temperature is diagnostic only. Executing SRK thermodynamics
owns temperature reconstructed from transported absolute enthalpy.

`node generate.mjs ORIGINAL_TABLE_DIR PHASE_JSON` prints a read-only plan. Add
`--out NEW_DIRECTORY` to write `passive.tbl` and a separate analytic manifest.
No original table or physical convergence/provenance receipt is rewritten.

`node configure.mjs NEW_CASE TABLE_DIRECTORY` plans replacement of the factory
table and original-zero species values. Add `--apply` only in a Slurm allocation.
The original factory manifest remains retained; `passive-cold-input.json` records
the active physics and changed-file hashes. Geometry, flow rates, pressure,
temperatures and the absolute-Ha guard remain unchanged. Fresh runtime Ha and
inlet-density preparation must follow before decomposition and CFD.

Dependencies: Node built-ins and the strict `steady-flamelet/input.mjs` loader.
Dependents: bounded G2 diagnostic run wrappers. No network, credentials, model
provider, scheduler submission, library change or EOS parameter change occurs.
Paths and site-specific Slurm configuration belong to external run wrappers.

Verification: syntax checks; read-only generation on the retained physical table;
endpoint/affine/source checks, including rejection of a nonzero chemical-source
mutation; then actual library initialization, all-rank CFD and conservation
observations. These checks do not grant scientific or human acceptance.
