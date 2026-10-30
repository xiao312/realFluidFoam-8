# Approximate quench/chemistry water-progress manifold

This bounded experiment constructs a separate diagnostic FGM manifold from
retained physical quench states and fresh homogeneous constant-pressure chemical
tails. It does not overwrite the existing table, reproduce Sharma's different
mechanism/pressure, or claim that a single progress coordinate is globally exact.
The transported candidate is the unnormalized mass fraction sum
`Cwater = Y_CO2 + Y_CO + Y_H2O`; its source is kg/m3/s, not 1/s.

## Physical construction

At each of the retained 129 mixture-fraction nodes, select the actual post-maximum
quench state nearest 1500 K with nonnegative composition. The target temperature
chooses an existing physical seed, not a prescribed temperature reset. The cold
portion of that same quench trajectory is retained. A new adiabatic ideal-gas
constant-pressure reactor starts at exactly the selected T/Y and 5.61 MPa and
integrates all 53 GRI species plus energy for 200 microseconds. No CFD state is
continued. Cantera 3.2/CVODE and the exact mechanism are reused without rebuilding.

An explicitly ordered ascending-progress branch joins the cold physical states
to the chemical tail. Reversing/redundant states and their exact indices are
retained as omissions. The highest observed chemical-tail state with nonpositive
progress source is preferred as the upper bound; if none exists, the actual
outward source remains and the table is diagnostic-only. Sources are never
forced to zero. Pure-stream rows remain their original boundary states.

Table interpolation uses mass fractions and specific enthalpy; the unchanged
Cantera model inverts HP for temperature and recomputes the actual chemical
source, formation heat release and density. It does not fit sources to a paper.
Even-indexed Z nodes (65) train the table; odd nodes (64) provide independently
integrated held-out branches. Temperature, composition, source, energy and
coverage errors are reported separately. No automatic scientific acceptance.
Every training branch is required. A failed held-out branch is preserved as
missing validation coverage and does not destroy an otherwise available
diagnostic table; it cannot become a fabricated passing observation.

## Inputs, outputs, policies

`run.py --raw-dir DIR --settings settings.json --mechanism gri30.yaml --plan`
checks the frozen raw trajectory/receipt/metadata identities and reports a
read-only plan. An actual run additionally requires `--out NEW_DIR`,
`--source-commit SHA`, `--environment-sha256 SHA` and a Slurm allocation.
`settings.json` pins the input hashes, model, integration and numeric policies.

The output retains each accepted chemical tail and selected branch in compressed
arrays, original source/endpoint diagnostics, all omission indices, `physical.tbl`
with the existing explicit v2 grammar and three progress species, table/held-out
diagnostics and a physical-family-table/v1 receipt. A successfully written table
does not imply inward source bounds, sufficient CFD coverage or paper agreement.

Only declared mass-fraction roundoff is projected: negative values below -2e-10
fail, changes above 2e-9 fail, and progress species cannot be negative. A largest
non-progress species restores mass. A cold numerical progress tail at or below
1e-24 is set to exact zero by removing only those progress species and restoring
the same mass; every change, elemental/enthalpy effect and recomputed source is
recorded. Raw arrays never change. Exact selected join states need no negative
projection; unavoidable floating-point normalization is measured.

## Postprocessing a retained physical family

`derive.py` does not integrate any reactor. It requires the exact original failed
receipt hash and every branch/receipt hash, a new output directory, and the
explicit `--endpoint-policy existing-bounded-roundoff-v1`. The original driver
remains unchanged. Only a negative measured endpoint invokes the already declared
roundoff bounds. The derived receipt retains species, elemental composition,
enthalpy, progress source and formation heat release before/after that operation.
Nonnegative endpoints remain byte-value unchanged; sources are recomputed only
where the representation changed. A source sign is never forced or accepted.
The original physical JobID and source remain separate from the derivation job.

Use `derive.py --input DIR --input-receipt-sha256 HASH --settings settings.json
--mechanism gri30.yaml --endpoint-policy existing-bounded-roundoff-v1 --plan`
before an allocated exact-runtime derivation. Missing branches, material negatives,
changed inputs or unsupported policies fail without new physical computation.

## Boundaries and verification

Dependencies are Python, NumPy and the pinned Cantera runtime. The retained
direct-flamelet results supply inputs; the separate OF8 v2 table reader is the
potential dependent. No controller, scheduler adapter, secrets or network access
are embedded. All remote paths are explicit caller inputs, all outputs are new.
Large arrays remain outside Git. Physical integration runs only in an allocation.

Use the read-only plan and `git diff --check`; exercise the same frozen module
inside the next allocated batch. That batch must retain actual integration
completion, conservation, branch omissions, upper/lower source signs and held-out
errors before any CFD use. The original FGM failure and independent fixed-chi
SLFM diagnostics remain separate. Source/energy projection error is measured;
no coefficient tuning or relaxed acceptance is hidden in this experiment.
