# FGM in the OpenFOAM-8 fork: table/interface and ownership contract

## 2026-10-31 scope amendment

The original v1 proposal below is retained as development history. Current
interfaces are documented in [fgmTable](../../src/combustionModels/fgmTable/README.md)
and [reactingFoamSolveZ](../../applications/solvers/reactingFoamSolveZ/README.md).
The latter transports Z and raw progress; v2 normalizes lookup coordinates only.
Positive Q on the sensible-energy equation's right-hand side heats the fluid.
The original fixture statement that negative Q is exothermic is not that solver
convention. The opt-in absolute-enthalpy equation omits chemical Q and obtains
sensible enthalpy from total enthalpy and composition. Diagnostic bounds clipping
is counted explicitly. The older fixed-Z and source-only energy descriptions
below do not describe these extensions. The utility/check paths below refer to
the historical worker tree; this checkpoint uses the direct-verification module.
These revisions remain candidates until executed checks and review qualify them.

## Original v1 proposal

Status: proposed, unbuilt in the executing image as of the commit that adds it.
Nothing in this document is a physical result, a criterion, or an approval.
It is the interface boundary that the OpenFOAM-side FGM runtime is written
against, so that the table producer and the solver cannot silently disagree
about who owns density, temperature, enthalpy or the source units.

## 1. Scope

This contract covers the OpenFOAM side only:

| Path | Role |
| --- | --- |
| `src/combustionModels/fgmTable/fgmTableReader.{H,C}` | strict reader + bilinear interpolator for the forge table |
| `src/combustionModels/fgmTable/fgmTable.{H,C}` | `combustionModel` that drives composition, progress source and heat release from the table |
| `src/combustionModels/fgmTable/fgmTables.C` | run-time registration for `psiReactionThermo` and `rhoReactionThermo` |
| `applications/utilities/fgmTableProbe/` | mesh-free utility that loads a table and reports lookups |
| `replication/validation/fgm-of8/checks/fgm-table.py` | independent Python reference for the same format |
| `replication/validation/fgm-of8/checks/run-fgm-build.sh` | staged compile/load/lookup diagnostic |

The table *producer* (tabulation, flamelet library, mechanism choice, table
provenance) is outside this contract and belongs to the FGM worker. The two
sides meet only on the immutable artefacts described in §7.

## 2. Ownership: exactly one owner per quantity

The donor analysis (`/references/recovery-20261025/fgm-reuse.md`, written
against DeepFlame pin `7cb3294b275525cb8829ada3d3fbc067ab9323eb`) records the
central hazard: an FGM implementation that reconstructs enthalpy or multiplies
its source by a density again will double-count, and in a real-fluid solver it
will also fight the equation of state. The boundary below removes that
possibility by construction.

| Quantity | Owner | Notes |
| --- | --- | --- |
| density `rho` | the thermophysical model (`thermo.rho()`) | never written by this module; no `rho = p*W/(R*T)` anywhere on this path |
| temperature `T` | the thermophysical model | obtained from `thermo.he()`, never from the table |
| enthalpy `h` / energy variable | the thermophysical model | never reconstructed from the table |
| species mass fractions `Y_i` | this module, from the table | overwrite the mixture's `Y()` fields each `correct()` |
| progress variable `c` | the solver, with the table's source | transported like any scalar; table supplies source and the `Sc` closure |
| progress-coordinate declaration | the table | `mass-fraction` or `normalised`; the c axis is a coordinate, and which one it is may not be guessed |
| progress source units | `kg/(m3 s)` | inserted as an explicit volumetric source, no `rho` factor applied here |
| progress source value | the table, converted once | the `Sc` block is the source of the composition variable `Yc`; the source of the transported coordinate is `Sc` for a mass-fraction coordinate and `Sc/dYc` for a normalized one |
| heat release `Qdot` | the table | `W/m3`, sign convention of the table (negative = exothermic in the fixtures); returned verbatim |
| tabulated temperature `Tdiag` | diagnostic only | written to `fgmTdiag`, never read back into the thermo |

Consequences that the implementation must keep true:

1. The table header declares `density-owner`, `temperature-owner` and
   `enthalpy-owner`, and every one of them must read `thermophysicalModel`.
   A table that claims one of these is refused before a single lookup happens —
   in both the Python reference and the C++ reader.
2. `fgmTable::correct()` writes `Y`, `fgmSc` (the tabulated block for `Yc`),
   `fgmScSource` (the source of the transported coordinate), `fgmQdot` and
   `fgmTdiag`, and nothing else. It never writes `p`, `T`, `h`, `rho` or `U`.
3. The energy equation keeps using the thermophysical model's `he`/`h` and
   `thermo.correct()`; the table contributes through `Qdot()` only.
4. The solver must not also solve species equations while the composition is
   tabulated. The base class exposes `compositionTabulated()` (false for every
   reacting model, true for `fgmTable`) so the guard is a property of the
   model, not a switch a case can forget. `R(Yi)` returns an empty matrix so
   that a solver which ignores the guard produces a visibly unsourced species
   equation instead of a silent mixture of tabulated and solved species.

## 3. Table format (`forge-fgm-table-v1`)

Plain text, one `key value` header per line, then `block <name>` … `end`
sections. Required headers:

```
schema forge-fgm-table-v1
source <provenance string, quoted>
profile-sha256 <64 hex>
units-progress-source kg/m3/s
units-heat-release W/m3
density-owner thermophysicalModel
temperature-owner thermophysicalModel
enthalpy-owner thermophysicalModel
progress-coordinate <mass-fraction|normalised>
progress-dYc <dimensionless width, required iff normalised>
species <n> <name>...
nZ <n>   nC <n>
z <nZ values, strictly increasing>
c <nC values, strictly increasing>
```

### 3.1 The progress coordinate, and why it must be declared

The `c` axis is a *coordinate*, not necessarily a mass fraction. With

```
c = (Yc - Yc_min)/dYc
```

the volumetric source of `c` is `omega_Yc/dYc`, while the `block Sc` the table
carries is `omega_Yc`, the source of `Yc`. Two things follow, and both are
enforced rather than assumed:

1. A table must declare which coordinate its `c` axis is. `mass-fraction` means
   `c` *is* `Yc`, so `Sc` is used as it stands. `normalised` means `dYc` must
   also be declared and the runtime divides `Sc` by it. A table that declares
   neither, or `normalised` without `progress-dYc`, is refused: a missing
   factor of `dYc` is a wrong source, and a guessed factor is a silent model
   change.
2. `dYc` is one dimensionless width for the whole table. A coordinate whose
   normalization varies in space is not expressible in this format, because the
   conservative equation `ddt(rho c) + div(phi c) + divj(c) = Sc/dYc` would then
   carry an additional transport term for the normalization itself. The reader
   refuses rather than writing that term as zero.

The conversion appears in exactly one function — `fgm::fgmTableReader::sourceOfC`
and its Python twin `fgm.source_of_c` — and the model returns its result from
`progressSource()`. The raw block is still written as `fgmSc`, so a run shows
both the tabulated quantity and the quantity that entered the equation; the
converted field is `fgmScSource`. Nothing here is a physical normalization: the
fixtures' `dYc` is a fixture number, and a physical FGM table's `dYc` must come
from the flamelet that defined `c`.

`omega_Yc` is a volumetric rate in `kg/(m3 s)`, not a time derivative of `c`:
`ddt(rho c) = omega_Yc/dYc` is the equation, and for a mass-fraction coordinate
the naive `ddt(c) = Sc` reading is off by both `rho` and, for a normalized
coordinate, `dYc`.

Blocks: one `block Y <species>` per declared species, plus `block Sc`, `block Q`,
and the optional `block Tdiag`. Each block holds `nZ` rows of `nC` values.

The format is ours. It is deliberately **not** the donor's FlaRe format: the
donor's reader expects a binary/ASCII layout with its own conventions, and
adopting it would couple our provenance and refusal semantics to a format we
do not control. Borrowing code is allowed and is recorded where it happens;
borrowing a format would quietly import assumptions (including the ideal-gas
`psi` path) that this solver must not inherit.

## 4. Refusals (validation before runtime, never repair)

All of the following are fatal, at load or at lookup, with the measured value
printed. None is clamped, rescaled or tolerated, and there is no option to
widen one:

- unknown schema; missing or duplicate header; unparsable number; duplicate block
- `nZ`/`nC` disagreeing with the grids, or a grid with fewer than two nodes
- a grid that is not strictly increasing
- a missing required block; an unknown block; a short or long row
- species not summing to 1 at a node within `1e-8`
- a negative mass fraction beyond a `-1e-12` round-off allowance (sources and
  heat release may be negative; species may not)
- units other than `kg/m3/s` and `W/m3`
- owners other than `thermophysicalModel`
- a missing or unrecognised `progress-coordinate`, a `normalised` table without
  `progress-dYc`, a non-positive or unparsable `progress-dYc`, or a stray
  `progress-dYc` on a mass-fraction table
- a lookup point outside the tabulated box under `boundsPolicy error`

The bounds policy is explicit and case-declared: `error` (default) aborts,
`clamp` selects the boundary cell and returns the boundary value. Clamping is an
opt-in declaration in the case dictionary, never a fallback, and a clamped run
must say so.

## 5. Runtime contract

Case dictionary (`constant/combustionProperties`):

```
combustionModel fgmTable;
fgmTableCoeffs
{
    table               fgm/table.tbl;   // relative to constant/, or absolute
    boundsPolicy        error;           // error | clamp
    mixtureFractionField Z;
    progressField       c;
    speciesSumLimit     1e-8;
}
```

Fields: `Z` and `c` are read (`MUST_READ`) from the case; both are written back
(`AUTO_WRITE`) so a run leaves its own state. `fgmSc`, `fgmQdot` and `fgmTdiag`
are derived and written.

Each `correct()`: interpolate at every cell, overwrite the thermophysical
species, set the three derived fields, accumulate the worst `|sum(Y)-1|`, and
refuse if it exceeds `speciesSumLimit`. The log line per call carries the cell
count, the `Z` and `c` ranges, the source range, and the worst species-sum error,
so that a later log gate can decide without being told.

Species are mapped by name: every table species must exist in the
thermophysical mixture and every mixture species must have a table block. A
mismatch in either direction is fatal — no default, no zero-fill, no silent
drop.

The progress-variable equation is the solver's, not this model's, and it must:

```
ddt(rho*c) + div(phi*c) - div(Gamma_c grad(c)) = Sc
```

with `Sc` in `kg/(m3 s)` taken from `fgmSc` **without** multiplying by `rho`
again. That equation now exists: `applications/solvers/reactingFoam/cEqn.H`,
reached only when the model reports `transportsProgress()`, with the source
fetched from the model object (`progressSource()`) rather than from a field
looked up by name, so a case cannot point the solver at the wrong field.
`YEqn.H` is wrapped in `!reaction->compositionTabulated()`, and in that branch
it deliberately performs no inert-species bookkeeping: the model owns the
composition, and overwriting the inert species here would be a second, silent
repair.

Three declared assumptions of that integration, none of them measured:

- `c` is diffused through the same thermophysical transport model as a species
  mass fraction (`divj`). The table carries no progress diffusivity and no
  Lewis number, so inventing one would be a silent model change.
- the source is added explicitly, in the table's own `kg/(m3 s)`. A tabulated
  `Sc(Z, c)` has no derivative in the table, so no linearisation in `c` is
  attempted.
- `Z` is read and not transported. A transported mixture-fraction equation is a
  later, separate change; until then a run exercises the table at one fixed `Z`,
  and such a run is plumbing evidence, never a flame. `c` is expected to be bounded in `[0, 1]` by the transport solution;
the model's own declared bound is the tabulated grid, and `boundsPolicy error`
turns a transport overshoot outside the grid into a refusal rather than a
clamp. If a run needs `clamp` to survive, that is a finding about the case, not
a licence to widen the table.

## 6. What was not copied from the donor, and why

The donor sources named in the order (`baseFGM.C`, `flareFGM.C`,
`tableSolver.{C,H}`, `readThermChemTables.H`) are **not readable in this
environment**: there is no DeepFlame tree on any mount at pin
`7cb3294b275525cb8829ada3d3fbc067ab9323eb`, and there is no network egress. The
boundary above is taken from the campaign's own prior inspection of exactly
those files (`/references/recovery-20261025/fgm-reuse.md`). Until a read-only
staged copy of the pin is available, no line of donor code is claimed to have
been read, borrowed or rewritten here.

Explicitly **not** inherited from the donor's ideal-gas path:

- `psi = W/(R*T)` and `rho = p*psi` — the fork's real-fluid thermo owns `rho`
- enthalpy reconstruction from table enthalpy columns
- any multiplication of a tabulated source by a density
- the donor's six-coordinate lookup as a minimum viable requirement: this
  module is two-coordinate (`Z`, `c`) and says so; adding coordinates is a table
  format change under a new schema, not a runtime switch

## 7. Handoff and immutability

The table is handed over as an immutable artefact: the exact bytes, their
sha256, and the `source`/`profile-sha256` headers inside them. The handoff goes
through the reviewer, not through shared edits; the OpenFOAM side owns
`applications`, `src` and the allowed replication paths, the FGM side owns
`replication/fgm`. A table whose bytes change after a run is quoted is a
different table: supersession is stated in a new file with a new hash.

## 8. Evidence classes

Reported separately, always, and never merged into one verdict:

| Class | What it would establish | Status |
| --- | --- | --- |
| compile | the committed sources build against the executing image | pending job `of8-fgm-build-1` (probe + library); the solver integration compiles only with a full solver build |
| load | the built module registers and is selected by the case dictionary | pending the same job, for the probe; registration in a solver is `makeCombustionModel` syntax only |
| table read + lookup | the reader parses/refuses as contracted, and C++ agrees with the Python reference numerically | offline checks green (21 Python tests, 3 build-script guards); in-image run pending |
| field update | `correct()` sets `Y`, `fgmSc`, `fgmQdot` from a real table in a real mesh | not attempted; needs a solver run on a mesh, which is a separate job |
| flame agreement | the tabulated chemistry reproduces a measured flame | not attempted, not claimed, and not reachable from any of the above |

A pass in the first four says nothing about the fifth. No tolerance, reference
value, coefficient or criterion may move because of any result in this table.

## 9. Declared limits of this document

- No generated table exists in this repository; the two fixtures are synthetic
  and exist to exercise the format, the arithmetic and the refusals.
- The progress-variable `Sc` closure is tabulated, not derived; its provenance
  is the table producer's and is carried in the header only.
- No claim is made about `energy-species-coupling`, about a G2 flame, or about
  any figure. The G2 real-flow diagnostic remains blocked on a separate,
  proposed dictionary correction (`noCombustion` → `none`) that needs an order.
- The solver integration is source, not evidence: it has neither been compiled
  in the image nor run. A compile failure there is a defect in this patch, and a
  successful compile still says nothing about the chemistry.
- `Tdiag` is a diagnostic and is not a temperature solution. A run whose
  `fgmTdiag` disagrees with `T` is reporting, not failing.
