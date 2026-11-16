# Retained G2 temperature fields

`audit-chemical-source.py --cells THERMAL_AUDIT_CSV --thermal-audit AUDIT_JSON
--species-collection RECEIPT
--metadata PHASE_JSON --mechanism AUTHOR_YAML --out NEW_DIR [--apply]` compares
stored volumetric CO+CO2 source with independently evaluated Cantera rates at
the captured composition. Three evaluations separate stored-table temperature
at reference pressure, actual temperature at reference pressure, and actual
T/p. This is ideal-gas concentration chemistry consistent with the table's
Cantera phase, not an independent real-fluid rate law or a CFD chemistry step.
No integration, normalization, source correction or acceptance occurs. Raw
case-sensitive species archive, member hashes, actual-cell audit and mechanism
identity must match. Outputs bind code/Cantera binary/input hashes and retain
per-cell rates; volume-integrated absolute differences avoid signed cancellation.
Cantera3.2 and NumPy are local postprocessing dependencies; no HPC or network
interface, credentials or remote writes. Default is read-only. Verify species
order, unnormalized composition retention, source units and independently
recomputed representative cell rates. Never interpret a small whole-domain
error as hot-front agreement or a changed source as a calibrated repair.

`audit-species.py --collection RECEIPT --metadata PHASE_JSON --wedge-degrees 5
--out NEW_DIRECTORY [--apply]` measures actual species/element/raw-progress
consistency. Its default is read-only. The receipt additionally binds the
original case-sensitive archive and each member hash. H and h remain distinct
in that archive and must never be extracted together onto a case-insensitive
filesystem. The tool reads species directly from archive members and verifies
their Foam object names. Metadata composition/molecular weights determine
element masses; no normalization, chemistry fitting or field correction occurs.
Outputs include mass-sum, CO+CO2 progress and elemental mixing-line deviations,
with mass-weighted integrals and worst-cell indices. Geometry uses the existing
renderer. Dependencies remain local NumPy and standard Python. It neither
performs EOS recovery nor grants physical acceptance. Verify exact metadata
binding, archive identity, one-to-one cell mapping and independent element sums
on actual fresh-zero CFD snapshots before interpreting the deviations.

`audit-cell-state.py --collection RECEIPT --wedge-degrees 5 --out NEW_DIRECTORY`
compares executing CFD temperature with the table diagnostic at the same
internal cells. The default is read-only; `--apply` writes JSON and per-cell CSV.
It verifies every collected hash, partition ownership and the actual wedge
angle, then integrates polygon first moments to obtain cell volumes. Inputs
must also contain `fgmTdiag`, `fgmScSource`, `rho`, `Z`, `c`, `Ha` and `p`.
Outputs include volume-weighted temperature differences, absolute-source
weighted differences and source fractions in cold or thermally displaced
cells. Absolute source weights prevent positive and negative chemistry from
cancelling. This is a state-consistency diagnostic, not a source correction,
boundary interpolation, equilibrium calculation or scientific acceptance.
Boundary diagnostics are deliberately excluded because their current stored
values can be stale. Verify that summed volume matches the executing energy
state and that all cells are mapped once; compare the CSV sums independently.
It reuses only the local renderer's mesh reader and NumPy; no new network,
secret, scheduler or solver dependency is introduced.

`render-case.py --collection RECEIPT --out NEW_DIRECTORY` renders one retained
case at its explicitly recorded time and rank count. Its default `--plan` mode
checks receipt and input hashes without writing. The receipt uses
`retained-cfd-cell-field/v1`, with `localRoot`, `case`, `sourceJob`, `ranks`,
`timeDirectory`, `time_s`, `archiveSha256` and per-file `inputHashes`.
It requires original-zero provenance, maps every global cell exactly once,
and retains instantaneous/non-accepted labels. The output includes actual
cell polygons/data, full-domain and injector-detail PNGs, and a hashed receipt.
This general interface supports the tapered-injector mesh as well as the older
exit-only meshes; it does not imply that their physical results are comparable.
Use `--apply` to render; verify positive finite fields, polygon areas, exact
cell mapping, source identities and image layout. Dependencies and storage
boundaries are the same NumPy/Matplotlib/local-only ones documented below.

Render completed OpenFOAM cell temperatures without advancing CFD. This module
does not submit jobs, restart cases, interpolate fields, or declare validation.

## Inputs and outputs

`--root` selects an explicit local evidence directory. Each `<case>-collection.json`
contains `localRoot`, `case`, `sourceJob`, `time_s`, `archiveSha256`, and
`inputHashes`. Supported cases are `schmitt` and `cavalieri`, at 5 ms.
Each collection contains the original ASCII mesh, 32 temperature partitions,
and their `cellProcAddressing` lists. Every input hash must match.

The renderer checks that each global cell receives exactly one finite positive
temperature. It projects actual mesh vertices to axial/radial polygons and draws
piecewise-constant cell values. Outputs are PNG fields, cell-data NPZ files and
`temperature-field-evidence.json`. No smoothing or triangulation is applied.

## Dependencies and boundary

Use Python 3, NumPy, Matplotlib and Node.js. The local Forge importer consumes the images
and evidence; the solver and HPC controller do not import this module. Files stay
under the selected root. No credentials, network connection or remote writes are
required. Raw fields and supplied papers remain outside Git.

## Example and verification

```sh
python plot-temperature-fields.py --root /project/selected-temperature-fields --plan
python plot-temperature-fields.py --root /project/selected-temperature-fields
```

The plan lists input receipts without writing. Rendering must map 20,000 Schmitt
and 10,000 Cavalieri cells exactly once for the retained R66/R67 snapshots. Verify
input hashes, positive polygon areas, field extrema, image layout and provenance.
These checks establish rendering integrity, not scientific agreement.

`import-targets.mjs` reads `selected-targets.json` and the rendered evidence from
`--root`. It adds four targets to an explicit `--catalog` and local `--site`.
Use its default read-only plan before `--apply`. It preserves previous targets,
captions and primary profile comparisons, and retains a pre-write backup.
It adds no papers to Git and has no remote publication interface.

```sh
node import-targets.mjs --root /project/fields --site /project/site --catalog /project/catalog.json
```

After applying, verify all original target IDs, four new IDs, captions, image/data
hashes, mean-versus-instantaneous labels, citation backlinks and HTML delivery.

```sh
node verify-import.mjs --root /project/fields --base http://127.0.0.1:8787/
```

The verified evidence has 75 targets, preserves the original 71 in relative order,
and leaves their captions and primary comparison images unchanged. A labelled
axisymmetric reflection provides a second near-field display. It adds no cells
or information to the simulated upper half-domain.
