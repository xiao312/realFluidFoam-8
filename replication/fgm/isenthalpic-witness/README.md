# Same-Z/C/enthalpy composition-history witnesses

This bounded diagnostic removes the enthalpy difference from the two retained
physical mixing witnesses. It keeps each complete original species composition
and the common pressure, mixture fraction and Cwater=YCO2+YCO+YH2O. Both new
states receive one target enthalpy: the arithmetic mean of their original
specific enthalpies. Cantera HP inversion supplies each temperature; a recorded
Cp-based correction finishes numerical inversion if necessary. This is a fresh
initial-state construction, not continuation of a previous reactor or CFD state.

Two fresh constant-pressure, adiabatic GRI/CVODE reactors run for 20 ms. The
original table, model coefficients and old trajectories remain unchanged. No
third trajectory or large test sweep is included. If their sources/trajectories
still differ, that establishes non-uniqueness for these two compositions in a
global Z/C/h description. It does not disprove a deliberately restricted,
physically selected manifold or establish a replacement closure.

The exact phase reports `thermo_model=ideal-gas`, `kinetics_model=bulk`, phase
`gri30`, and `transport_model=none` in Cantera3.2.0. These are ordinary gas-phase
GRI rates with the ideal-gas concentration/pressure relation, not an SRK
full-chemistry reactor. The matching extension binary hash establishes runtime
identity, not automatic activation of a nonideal model. Execution records these
actual model identifiers and rejects an unexpected thermo/kinetics selection.
This experiment isolates manifold composition/history for this declared model;
it does not qualify nonideal chemistry or change the SRK CFD closure.

## Interface and provenance

`run.py` consumes the hash-bound mixing-witness receipt, the two initial-state
JSON files bound by that receipt, its original long-table receipt and the exact
GRI mechanism. It verifies the source chain and matching species order before
preparing states. Execution uses the same pinned Cantera 3.2 extension as the
original physical witnesses. `--plan` reads identities without chemistry;
`--audit-only` permits only two local initial-state thermodynamic/source probes,
retains that different runtime identity, and never integrates. Actual execution
requires a Slurm allocation and exact source/environment identities.

Outputs: each original/requested/achieved h and thermal adjustment, original and
new Y, pressure, elemental and C invariants, accepted physical trajectories,
CVODE/conservation receipts, common-coordinate source comparisons, and first
crossing times for progress increments. The requested h values are identical;
achieved inversion residuals must be <=1e-6 J/kg and pairwise delta <=2e-6 J/kg.
The maximum Y adjustment is <=1e-14 and each seed's elemental/C change <=1e-12.
The retained pair already differs in elemental mass fractions by about7.55e-12;
that difference is preserved and checked against its existing1e-10 limit,
not removed by changing the supplied compositions. Both nominal and computed
Bilger Z are reported, with computed pairwise difference required <=1e-10.
Unmet initial-state equality blocks physical integration, preserving diagnostics.
Each independent reactor retains its evidence if the other fails. Numerical
completion is separate from scientific acceptance.

Dependencies: Python, NumPy, Cantera 3.2, and unchanged `hybrid-water/states.py`
and `tails.py`. The latter supplies the same full-species constant-pressure
reactor, rtol=1e-10, atol=1e-18, maximum step=10 microseconds, element/enthalpy
checks, and optional HP-equilibrium endpoint. The physical horizon is at least
20 ms because accepted CVODE steps may slightly pass the requested end; the
actual final times are recorded. Per-reactor wall ceiling is 30 s and the step
ceiling is 200000. There are no network, scheduler, credential or publication
operations in this module. Output directories must be new.

```sh
python replication/fgm/isenthalpic-witness/run.py \
  --mixing /retained/mixing-witness-r1/run --mixing-receipt-sha256 HASH \
  --primary /retained/hybrid-water-long-r2/run \
  --mechanism /pinned/cantera/data/gri30.yaml --plan
```

Verification uses the exact retained pair for a bounded initialization audit,
then the two allocated physical trajectories. Source archive and all input
hashes are checked before execution. No synthetic pass counts substitute for
physical equality, conservation or trajectory evidence.

`render.py --input RETAINED_R2 --prior RETAINED_MIXING_R1 --out NEW_REVIEW`
compares both new physical histories with the corresponding original histories.
Omit `--out` for a read-only identity check. It validates both receipt chains,
initial-state, physical-receipt and trajectory hashes, and requires matching
mechanism-runtime identities. Matplotlib is a rendering-only dependency. The
figures connect actual accepted CVODE states without smoothing or regression;
first-crossing times are reported as accepted-step brackets, not exact events.
The original enthalpy difference and the achieved equal-h residual remain visible.
This postprocessor performs no chemistry, table modification or publication.
