# G2 overnight coupling controls

Responsibility: reproducible original-zero pressure/coupling and property diagnostics for the owner window ending2026-11-16 09:20Asia/Shanghai. Not production qualification or a replacement for the fixed paper ladder. Inputs: exact prior qualified binary/library receipts, registered case/table/thermo and frozen per-run scripts. Outputs: new cases, raw physical profiles, audits, terminal receipts and later paper comparisons. All failed runs remain evidence.

Dependencies: source-clock-S13 qualified solver80fa810, R54 thermo51075d5, the direct-G2 factory and shared one-cell property probe. HPC execution is external through pinned FlamePilot Slurm adapters; no scheduler/model-provider dependency in the solver. Dependents: existing g2-paper-review/Forge figure import. No credentials in inputs; all writes/caches/logs remain inside the configured project root.

Each case script performs a read-only plan before mutation and refuses evolved/decomposed output. Minimal example: plan the ignored request with the FlamePilot adapter, then submit its exact frozen key. Inside the allocation main.sh verifies input and runtime hashes before preparing a fresh case.

Verify node --check for helpers, bash -n for wrappers, input manifests and actual executing pressure/source/energy controls. Check source/binary/case identities independently. Read physical profiles, continuity, EOS density, caloric and energy/source diagnostics; normal exit is not paper agreement. Compare matched physical times and preserve the current best view when a new diagnostic is worse.

`audit-oxygen.py --results EXPORT --thermo EXACT_DICTIONARY --out REPORT`
independently reconstructs the pure-O2 S20 SRK pressure, caloric properties and
analytic Cp identity, then checks homogeneous recovery of the retained rounded
S18 rho/e failures. Uses Python standard library only; no solver writes or
compute submission. Its expected verification is agreement against all exported
rows, with unstable recovered states explicitly flagged rather than accepted.
Fixed-pressure finite differences can cross a cubic-root switch; that alone is
not evidence of an incorrect analytic Cp. This is not a phase-equilibrium flash,
and NASA extrapolation below200K remains unqualified.

`audit-oxygen-phase.py` takes the same arguments and requires NumPy. It rechecks
all3116 executing property rows, brackets the pure-fluid spinodals, solves equal
SRK residual Gibbs energies, then uses volume/energy lever rules for the two
rounded S18 failures. Expected outputs: bounded vapor fractions, Gibbs residual
near roundoff and preserved volume/energy. This is an independent scalar phase
diagnostic, not a multicomponent FGM closure or a qualified production flash.

Observed15November: all3116rows reconstruct pressure within1.29e-13relative and
Hs within6.99e-10J/kg. Analytic Cp agrees within3.63e-9relative even at the worst
near-critical row; the large finite-difference discrepancies are not evidence
of a generally incorrect Cp formula. The rounded S18 rho/e targets recover as
unstable homogeneous states (negative isothermal slope). Pure-O2 two-phase SRK
solutions exist at154.01755K/4.940324MPa and154.43902K/5.017372MPa, conserving the
specified volume and energy. This explains a failure mode in the pure-fluid
contact adaptation. It does not establish that the multicomponent G2 failures
have the same cause or that their physical solution requires a flash.

`node import-diagnostic-field.mjs SPEC SITE CATALOG [--apply]` appends diagnostic
views to the retained75-target/12-paper local Forge export. SPEC supplies id,
label, note, targets, image/evidence paths, inputSha256 and scientificAcceptance
false. The default is read-only. Apply backs up the catalogue/export, verifies
input hashes and preserves every non-view target field, including primary
comparisons and original captions. It submits no compute and publishes no site.
