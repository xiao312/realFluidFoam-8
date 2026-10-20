# Independent checks of the Takahashi pressure correction

21 October 2026, Asia/Shanghai. State: property calculations and source audit
completed; no scientific result accepted and no transport model changed.

The available primary evidence does not reveal a large implementation error
in the current Takahashi correction. At Meng's 200 K, 100 atm hydrogen/oxygen
state, the pressure-normalized result differs by **+0.273%** from the published
model value. The two readable hydrogen points in Takahashi's original chart
differ by approximately **+0.69% and +2.87%**. These are limited consistency
checks: Meng reports calculations, and Takahashi's plotted reductions also
contributed to constructing the correlation. Neither is independent validation
of reacting-mixture transport or an explanation of Liang's Figure 6.

## Meng 2005: all three tabulated diffusion states

[Meng et al., Table 2](https://yang.gatech.edu/publications/Journal/JFM%20(2005,%20Meng).pdf)
contains one temperature, **200 K**, and a **50/50 molar H₂/O₂** mixture.
The diffusivities are model outputs from Fuller dilute diffusion followed by
Takahashi, not measurements. The primary PDF text was readable; local HTTPS
download and visual-table retrieval failed. These values therefore remain
provisional transcriptions.

| Pressure, atm | Published D, m²/s | Published `pD/(pD at 1 atm)` | Rounding interval |
|---:|---:|---:|---:|
| 1 | 4.04 × 10⁻⁵ | 1 | Normalization anchor |
| 100 | 3.88 × 10⁻⁷ | 0.960396 | 0.957973–0.962825 |
| 400 | 9.92 × 10⁻⁸ | 0.982178 | 0.980470–0.983891 |

The interval assumes rounding to half the last printed digit in both numerator
and denominator. It is not experimental uncertainty. Normalizing at fixed
temperature and composition removes the dilute coefficient and isolates the
pressure correction.

## Evaluated reduction and interpolation

The physical input uses H₂ `Tc = 33.18 K`, `Pc = 1.300 MPa` and
O₂ `Tc = 154.58 K`, `Pc = 5.043 MPa`. Equal-mole arithmetic mixing gives
`Tc = 93.88 K`, `Pc = 3.1715 MPa`. The existing equation evaluates
Takahashi Table 2 at the actual reduced temperature, then linearly interpolates
between adjacent reduced-pressure rows.

The alternative labelled **chart interpolation** linearly interpolates
between the explicitly plotted reduced-temperature isotherms as well.
It retains every original coefficient. This is a numerical reading
sensitivity, not evidence of Meng's implementation. At 200 K the surrounding
isotherms are `Tr = 2` and `2.5`.

The historical **Newton diagnostic** changes only hydrogen's transport
reduction inputs by `+8 K` and `+8 atm`. Its provenance and the qualification
of its use in Takahashi's final chart are recorded in the
[reduction audit](liang-takahashi-reduction-audit-20261021.md).
It is not a proposed EoS change or a fitted correction.

| Pressure | Physical input, equation | Physical input, chart interpolation | Newton, equation | Newton, chart interpolation |
|---:|---:|---:|---:|---:|
| 1 atm | 1 | 1 | 1 | 1 |
| 100 atm | 0.963020 | 0.958707 | 0.952078 | 0.950194 |
| 400 atm | 0.980692 | 0.975437 | 0.968232 | 0.965912 |

At 100 atm, physical-input chart interpolation falls inside the rounding
interval; the equation result is slightly above it. Their relative
differences are +0.273% and −0.176%, respectively. Newton gives −0.866%
with equation evaluation and −1.062% with chart interpolation.

**The 400 atm row is outside the tabulated pressure range.**
Physical and Newton reductions give `Pr = 12.7794` and `11.3314`;
the table stops at 5. The numbers above retain the current implementation's
last-row cap. Its apparent agreement with the published value does not
validate that cap or attribute it to the paper. The 1 atm row likewise uses
the declared below-0.1 unity policy and is only the normalization anchor.

No absolute Fuller diffusivity was reconstructed, no missing diffusion-volume
constants were selected, and no interpolation method was fitted to these rows.

## Original Takahashi hydrogen evidence

The inspected [original 1974 paper](https://www.jstage.jst.go.jp/article/jcej1968/7/6/7_6_417/_pdf)
defines `(Dp)R = Dp/(Dp)^0`, with the reference product extrapolated to
1 atm at each temperature. Figure 1 is at `Pr = 1`.
Its open triangles identify hydrogen self-diffusion, pooling references
11 and 19. Two symbols can be read separately from surrounding markers:

| Symbol | Published Tr | Read `(Dp)R` | Current equation | Chart interpolation |
|---|---:|---:|---:|---:|
| A | 1.649 ± 0.010 | 0.929 ± 0.010 | 0.93542 | 0.93408 |
| B | 2.333 ± 0.010 | 0.963 ± 0.010 | 0.99100 | 0.98882 |

The bounds cover ±3 pixels for marker location plus ±1 pixel for axis reading
in the preserved three-times render. They are reading envelopes, not
experimental error bars. Axis skew is accounted for with local interpolation
of the zero and unity lines. Concealed symbols were excluded.

These are **experimental results reduced and interpolated by Takahashi**,
not original measured `T,p,D` triplets. The composition is chemically pure H₂,
but the figure does not identify the ortho/para composition or original source
of each marker. The original Table 1 explicitly notes that hydrogen's
normalized values were recovered from curves or experimental equations.

For a conditional sensitivity, treating those published reduced coordinates
as physical-critical coordinates and then substituting Newton's constants
gives 0.91761 and 0.97906. This transformation does not recover original
dimensional states. The sensitivity therefore cannot determine which
critical convention the original experiments or final chart used.
Nor can these correlation-construction points provide an independent
acceptance test.

## Original measurement access and excluded points

| Original source | Composition information | What is available |
|---|---|---|
| [Hartland and Lipsicas 1964](https://doi.org/10.1103/PhysRev.133.A665) | Pure hydrogen; 20–75% orthohydrogen | Publisher abstract: 20–55 K, densities to 850 amagats. Its ±10% absolute dilute-gas comparison is not transferred to unidentified chart points. Full numerical data were not obtained. |
| [Lipsicas 1962](https://doi.org/10.1063/1.1732719) | Normal hydrogen | Original title and bibliography verified through Takahashi reference 19 and NBS Monograph 168 reference 449. Original full numerical results were not obtained. |
| [Chou and Martin 1957](https://doi.org/10.1021/ie50568a043) | Trace ¹⁴CO₂ in CO₂/H₂ baths, with `x_CO2 = 0.790, 0.432, 0.266, 0.064` in Takahashi Table 1 | Original publisher record is accessible; full text is paywalled. Takahashi supplies ranges, counts and average discrepancies, not individual measurements. Its common chart symbol does not identify the bath composition of each point. |

The Chou data concern isotope-tracer diffusion in a mixed bath. They must not
be relabelled as finite-concentration H₂/O₂ binary or flame mixture-averaged
diffusivity. A 1955 Michigan dissertation by Chou was bibliographically
identified, but no open primary full text was recovered.

The bounded search covered original titles and DOIs, publisher records,
OSTI/NIST references and the Michigan repository. No raw numerical
measurement was imported from a secondary abstract. No author contact or
access-control bypass was attempted.

## Reproduction and decision

All generated files are in ignored
`state/liang-hydrogen-20261020/diffusion-primary-benchmark/`:

- `dataset.json` preserves values, source types, units, normalization,
  access limits, excluded symbols and pixel calibration.
- `benchmark.py` has a read-only default and writes only with `--apply`.
- `meng-comparison.csv`, `takahashi-H2-chart-readings.csv` and
  `takahashi-H2-comparison.csv` contain each evaluated state and diagnostic.
- `summary.json` records input hashes; `takahashi-figure1.png` and
  `takahashi-symbols.png` preserve visual evidence.
- `downloads.json` retains the failed local Meng download; no PDF hash
  is invented for that source.

Run from the project root using the existing analysis environment:

```powershell
state/analysis-venv/Scripts/python.exe -B state/liang-hydrogen-20261020/diffusion-primary-benchmark/benchmark.py
state/analysis-venv/Scripts/python.exe -B state/liang-hydrogen-20261020/diffusion-primary-benchmark/benchmark.py --apply
```

Both commands completed with exit status 0. The application evaluated
12 Meng combinations and 8 chart-point comparisons without launching a flame
or changing production code. Takahashi PDF SHA-256:
`88e9eaa011e6b17b4ea2dd1253c36e363865776f4c8a8fa4db8fb507ada3945e`.
Input table SHA-256:
`62f54b709d5cee57f1dd530fc12b30cf619db472ce886c95053b1f32c1ba01b0`.

Keep the current correction as an identified baseline. These checks support
its general normalization and numerical scale, while leaving its reacting
mixture extension and pressure-boundary policy unvalidated. They do not
justify modifying constants to reproduce Liang's unexplained ratio. A
stronger acceptance test needs original pointwise measurements with known
composition, an independently defined low-pressure reference, and states
inside the correlation's tabulated range.
