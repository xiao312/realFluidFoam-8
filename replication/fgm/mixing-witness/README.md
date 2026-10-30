# Physical mixing witnesses for progress-manifold coverage

This bounded diagnostic mixes actual retained burned-cap states with the two
original pure inlet streams, conserving species mass and specific total enthalpy.
The unchanged Cantera ideal-gas GRI model inverts HP to obtain each mixed
temperature. Fresh constant-pressure, adiabatic full-chemistry reactors then
follow the states for20ms. No CFD state, table bound or source is continued or
edited. This module does not construct or accept a replacement FGM table.

Four seeds test two questions. Two mix the actual Z=.43257258 cap with CH4 to
Z=.48531926 and .50503228, where current coverage is missing. The other two have
the same Z=.286519345725 and raw Cw=YCO2+YCO+YH2O but use different retained-cap
and stream combinations. Their T/Y/h/source differences test the adequacy of
the two-coordinate description without assuming uniqueness.

Inputs are the exact retained hybrid long-table receipt, table.npz, phase metadata
and pinned GRI/runtime identities. Every raw source state, mixing weight, element
vector, HP inversion residual and full composition is retained. Outputs include
initial-state comparisons, accepted physical trajectories, CVODE/conservation
receipts, progress reversals and actual same-coordinate table differences.
Out-of-range comparisons remain missing coverage rather than clamped data.

Dependencies are Python, NumPy, Cantera3.2 and the explicitly imported state and
reactor routines in `fgm/hybrid-water`. No scheduler implementation, network,
credentials or publication tools are embedded. Parent/operator Slurm admission
is required for physical integration; every output directory must be new.

Example (identities supplied explicitly):

```sh
python replication/fgm/mixing-witness/run.py --input /retained/long/run \
  --input-receipt-sha256 HASH --mechanism /pinned/gri30.yaml --plan
```

`--audit-only` with a fresh `--out` performs only four initial thermodynamic/rate
evaluations, records its local runtime identity, and never integrates. An actual
run additionally requires source/environment identities and an allocation.
CVODE tolerances remain1e-10/1e-18; maximum step10microseconds; each case is bounded
to20s CPU-wall observation and200000 accepted steps. Numerical completion and
scientific acceptance stay separate. Verification uses actual initial states
and allocated physical trajectories, not a synthetic pass battery.
