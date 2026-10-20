# Hydrogen comparison and isolated controls, 20 October 2026

The ideal hydrogen curve is close to Liang's original Figure 3, but the
nonideal curves have not passed. The original Figure 2 discrepancy and
Figure 6 conductivity discrepancy also remain. This does not authorize
promotion to new OpenFOAM cases under the owner's Cantera-first gate.

The source for the 48 initial pilot/sweep jobs is `ff39189850d8`,
build `125068607`. The 24 additional Case 2 jobs use that same binary.
The seven energy/transport controls use `50566574c293`, build `125070020`.
Global-grid and smooth-alpha controls use `cd62786661d0`, build `125071462`.
Each build passed the independent SRK, alpha and Takahashi checks plus 230
author binary/mixture diffusion checks. These checks establish implementation
properties, not agreement with the paper.

All cases use 100 atm, 298 K, O2/N2=21/79 molar, and the author Burke-2012
13-species/27-reaction mechanism. The displayed sweep uses LJ transport.
The author binary-polynomial variant is retained as a separate pilot. The
paper's Figure 4 ideal density independently supports the 298 K assumption.
Numerical guesses are for steady boundary-value solves; no CFD checkpoint is used.

## Quantitative pilot comparison

Figure 3 at phi=1.4, in cm/s:

| Case | Paper vector extraction | Current LJ baseline |
| --- | ---: | ---: |
| 1 | 75.828 +/- 0.084 | 76.0629 |
| 2 | 78.767 +/- 0.084 | 79.0301 |
| 3* | 75.478 +/- 0.333 | 75.9714, partial-temperature control only |
| 3 | 71.815 +/- 0.331 | 75.5094 |
| 4 | 70.184 +/- 0.349 | 76.2775 |
| 5 | 68.274 +/- 0.345 | 75.3396 |

The paper Case 3* implementation is unresolved; the current control cannot be
identified with it. Cases 4/5 paper values bridge short dash gaps, with an
explicit reading allowance. These are figure-derived values, not author tables.
The independent stock Cantera ideal solve gives 76.0691 cm/s.

The first energy controls at phi=1.4 give 75.5512 cm/s with matched advection,
75.4945 with pure-species diffusion enthalpy, and 75.5412 with both. None resolves
the approximately 3.7 cm/s Case 3 discrepancy. The reference-8 pure-temperature
approximation gives 78.6863 cm/s and is not a successful paper reconstruction.
Full unmodified conductivity raises Case 4 to 93.1579 cm/s, worsening agreement.

The C4 smooth-alpha matched-H and partial-T controls give 75.5291 and
75.5236 cm/s on about 1824 nodes. Their difference is much smaller than the
original-alpha controls, supporting the diagnosis of enthalpy jumps. Global
subdivision to 3631 nodes gives 75.4528 and 75.4474 cm/s. These results do not
support attributing the remaining paper mismatch to that jump alone.
The C4 continuation is a named diagnostic, not Liang's reported model.

## Conductivity mapping result

An independent Python replay matches 35 sampled C++ baseline conductivities
within relative error 5.5e-13. Sixteen pure-component coupled-map recovery
checks pass, and derivative step sensitivity is below 2.1e-10. The probe
evaluated 395 named frozen-state variants and did not solve flames.

At 300 K, 100 atm, fresh stoichiometric H2/air:

| Mapping/correction | Dense-increment lambda, W/(m K) | Ideal/real ratio |
| --- | ---: | ---: |
| Current partial-volume mapping | 0.063682 | 0.85886 |
| Coupled map, current constants and CORT | 0.063394 | 0.86278 |
| Coupled map, original TN1039 constants and CORT | 0.063187 | 0.86559 |

All remain below one, unlike the paper's displayed conductivity ratio.
Restoring these mapping details therefore does not resolve Figure 6.
The SRK prescribed-volume hybrid is not a full TRAPP reconstruction; it does
not solve the original methane reference EOS. No coefficients were fitted.

## Evidence and document placement

Operator state is `state/liang-hydrogen-20261020/` beneath the project workspace:
`jobs.json`, `energy-jobs.json`, `grid-jobs.json`, `digitized/reference.json`,
and `conductivity-probe/summary.json` retain exact inputs and results.
Large artifacts and downloaded author files remain outside public Git.

The reviewed six-page PDF is
`output/pdf/liang-hydrogen-20261020-2311-v2/liang-hydrogen-figures-2-7.pdf`.
Figures 3-7 were inserted between the existing Figure 2 and Figure 8(a)
sections. Figure 2's main image/result was replaced in place; its earlier
critical-consistency diagnostic and attachment were preserved.

[Lark Figure 3 comparison](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcncau3lkYNx1tf3nO69H8uCg)
and [Figure 6 comparison](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnmNd0DqmVKaq8mP2DKBGzve)
contain the original panels, overlays, explicit legends and qualification limits.
Newer Case 2/global-grid runs are separate evidence until the next gallery refresh.
