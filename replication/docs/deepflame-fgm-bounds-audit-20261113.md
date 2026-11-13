# DeepFlame FGM bounds: source inspection, 13 November 2026

The observed small excursion is primarily a bounds-policy issue. Our source-stage
entry check is much stricter than the inspected DeepFlame implementation. This
does not establish that clipping is harmless, or explain the larger radial-profile
discrepancy. No solver change or new CFD run was made during this inspection.

## Source identity

Inspected upstream deepmodeling/deepflame-dev master at immutable commit
7cb3294b275525cb8829ada3d3fbc067ab9323eb. Files were downloaded individually by
their Git paths, avoiding Windows case-collision problems. The operator directory
state/deepflame-fgm-audit-20261113 retains the API tree, source identity and files.
This is a source audit, not a completed DeepFlame simulation or binary comparison.

## What DeepFlame does

1. `baseFGM.C` solves mixture-fraction transport and then applies the configured
   scalar limits through `Z_.min(ZMax_)` and `Z_.max(ZMin_)`. The initialized
   bounds are0and1. Its non-spray path shows this at lines774–775.
2. The progress equation includes a tabulated source in the finite-volume equation.
   After solving, it applies `c_.min(cMax_)` and `c_.max(cMin_)`, lines827–828.
   These are scalar field caps, not our local-Cmax(Z) roundoff-only projection.
   The unscaled initialization refers to Ycmaxall_; do not assume that this
   member and tableSolver::cMaxAll_ are the same variable or cap.
3. `flareFGM.C`, lines243–257, uses raw progress directly for scaled tables, or
   divides unscaled progress by a locally looked-up Ycmax. It floors the divisor
   with `smaller` before normalization.
4. `tableSolver.C` locates the first/last interval for out-of-range queries,
   lines425–452. Its interpolation factor becomes0below the lower endpoint
   and1above the upper endpoint, lines483–498. lookup6d uses this function for
   every coordinate, lines842–866. Thus lookup saturates at the table edge.

The inspected path does not impose our64epsilon fatal check for a tiny local
progress exceedance. Local lookup saturation does not necessarily project the
transported raw progress field onto the same local upper bound. Field clipping
and lookup-coordinate clipping are separate operations.

## Our failure and the difference

For failed job127801087, Z=0.14312663723114 and transported C=0.17343764148411.
The actual executed table gives local Cmax=0.17343752899662626. Therefore:

- absolute exceedance:1.1248748374e-7;
- exceedance/Cmax:6.48576e-7, approximately0.65ppm or0.0000649%;
- normalized coordinate:approximately1.0000006486;
- our configured absolute allowance:64epsilon=1.4210854715e-14.

Under the analogous DeepFlame normalization, this query would select the upper
lookup endpoint. That is an inference from the source arithmetic, not evidence
that an otherwise identical DeepFlame simulation finishes or matches the paper.
Progress definitions, table coordinates and model options also differ.

Our `fgmTableSourceI.H` calls projectSourceRoundoff before advanceSource. It stops
when the transported input exceeds the local interval by more than64epsilon.
This particular exception occurs before integrating the second source half-step.
It is not proof that the source ODE integration overshot its boundary.

DeepFlame's inspected transport/source equation also differs from our fixed-state
Strang splitting. Copying its lookup saturation alone would leave our source-stage
entry exception intact. Evaluation-only saturation and transported-field correction
have different consequences for coordinate consistency and conservation.

## Engineering assessment

A roundoff-only guard is useful for testing arithmetic, but is too strict as the
sole operational policy for these transported fields. A sub-ppm excursion alone
does not indicate a major physical instability. Its frequency and accumulated
corrections remain unknown after the first fatal cell.

The practical next implementation should define a consistent, explicit boundary
policy for both property lookup and source entry. Record affected cells, maximum
normalized/absolute excursion and the integrated progress correction. Quantify
species/progress and energy consistency. Keep a strict diagnostic mode and fail
on large or persistent departures. Use a separate versioned development protocol;
do not relabel the historical strict run as passed.

The local normalized tolerance needs an absolute treatment near collapsed rows.
Do not apply one unqualified relative cutoff when Cmax approaches zero. A state
projection and a lookup-only policy need separate physical tests before choosing.

This repair should not become a prolonged prerequisite blocking independent
diagnostics. The145ms temperature RMS errors339.6/696.9K are a separate, much
larger scientific discrepancy. There is no evidence that this single small bound
excursion caused those profile errors.

## Primary sources

- [DeepFlame scalar transport and clipping](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/src/dfCombustionModels/FGM/baseFGM/baseFGM.C#L774-L828).
- [DeepFlame local progress normalization](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/src/dfCombustionModels/FGM/flareFGM/flareFGM.C#L243-L260).
- [DeepFlame endpoint interpolation policy](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/src/dfCombustionModels/FGM/flameletTableSolver/tableSolver.C#L425-L498).
- [Our actual terminal comparison](maders-figure4-status-20261113.md).
