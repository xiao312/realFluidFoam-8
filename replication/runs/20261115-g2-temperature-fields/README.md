# Retained G2 temperature fields

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
