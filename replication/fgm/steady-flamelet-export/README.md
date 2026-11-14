# Retained steady-flamelet export

Convert an actual physical profile into the fixed-chi C++ table format, without
integration, composition repair or node resampling. Reuse the converter from
commit e8055a9ea48597125d639d07c30fae70a7f78e34. This revision additionally accepts
the explicit Schmitt5.6MPa/83K O2/300K CH4 recipe. Original5.61MPa/85/288K remains.

Inputs: profile.csv, diagnostics.json and their hashed receipt; exact phase
metadata; new output directory. Output: steady.tbl, manifest and original input
receipts. Python standard library only. No network, scheduler, secrets or CFD.
The C++ steady-flamelet model and case generator consume these bytes.

Use `python convert.py --profile-dir FRAME --phase-metadata FILE` for a read-only
plan. `--allow-approximate` preserves and acknowledges an originally failed steady
criterion; it does not change that verdict. Add `--apply --out NEW --source-commit
SHA` to export. Species, mass/element balance, stream endpoints, file hashes and
original convergence flags remain mandatory and enter the manifest.

Verification uses an actual retained frame: run the plan, export, then load with
`mascotte-g2/steady-flamelet/input.mjs` to verify exact endpoints and an interior
lookup. No numerical/profile acceptance follows from a valid conversion.
