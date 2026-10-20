# Liang Figures 2 and 4: critical-pair and density consistency

21 October 2026, Asia/Shanghai. Status: tested diagnostic; no scientific
acceptance and no model change. Source checkout:
`fcd11507e74587a4e3aced0f383d630018121a01`.

Replacing the current mixture's critical pair with the pair read from Figure 2
would spoil its Figure 4 fresh-density agreement under either of two independently
declared temperature-dependence choices. At equivalence ratio 1, the unchanged
species-mixing EOS gives **83.129 kg/m3**. The replacement gives **80.756 kg/m3**
with mole-averaged acentric factor, or **80.623 kg/m3** with the exact effective
Soave slope of the unchanged species mixture. Figure 4's triangle occupies
**82.681–84.074 kg/m3**, with centroid 83.149 kg/m3.

This does not establish that every possible pseudo-fluid interpretation of
Figure 2 is impossible. A deliberately broad, unfitted acentric-factor interval
covers many Figure 4 readings. The result supports keeping the verified species
EOS and treating Figure 2 as a separate unresolved diagnostic, rather than
changing all flame calculations to reproduce its critical curves.

## Question and source boundary

The [previous density audit](liang-density-consistency-20261021.md) already
held the baseline attraction parameter fixed while substituting the Figure 2
covolume. That reduced density; at phi near 1, matching the Figure 4 midpoint
then required about 74% more attraction. This follow-up does something different:
it derives **both** critical attraction and covolume from the Figure 2 pair,
then supplies declared, unfitted temperature dependence.

Liang's equations (1) and (2) specify molar SRK pressure, mole-fraction mixing,
and linear covolume mixing. Figure 2 concerns mixture critical properties;
Figure 4 independently plots fresh H2/air density at 100 atm. The earlier
ideal-density reading gives an unburned temperature consistent with 298 K.
The figure's black triangles are the paper's Case 2 calculations, not independent
experimental density measurements.
[Liang, Li and Law, 2019](https://doi.org/10.1016/j.proci.2018.06.070).

The distinction between a fixed-composition pressure-volume inflection and a
true mixture phase-critical point remains unresolved in the published
implementation. The equations below apply to a **single SRK pseudo-fluid
constructed from the plotted pair**. They do not convert a general mixture
phase-critical point into valid species parameters. The
[critical-definition audit](liang-critical-definition-audit-20261020.md) and
[source follow-up](liang-figure12-followup-20261021.md) retain that limitation.

## Calculation without a fit

At fixed composition, the SRK pressure-volume inflection gives

```text
Omega_b = (cube_root(2) - 1)/3 = 0.08664034996495773
Omega_a = 1/[9(cube_root(2) - 1)] = 0.4274802335403414
b*  = Omega_b R Tc*/Pc*
ac* = Omega_a R^2 Tc*^2/Pc*
a*(T) = ac* [1 + m(1 - sqrt(T/Tc*))]^2
m(omega) = 0.480 + 1.574 omega - 0.176 omega^2.
```

Stars identify parameters derived from Figure 2. Exact inflection constants
preserve the plotted pair algebraically. The unchanged species baseline retains
its existing rounded pure-species coefficients, 0.42747 and 0.08664. These
rounding differences do not explain the discrepancies.
The temperature function and polynomial are Soave's original formulation.
[Soave, 1972, equations (5), (6), (13), and (15)](https://doi.org/10.1016/0009-2509(72)80096-4).

The frozen state is `T=298 K`, `P=10,132,500 Pa`, with molar proportions
`H2:O2:N2 = phi:0.5:0.5(79/21)`. Molecular weights and species critical inputs
come from the existing pinned `inputs-lj/species.txt`. The gas root of

```text
P v^3 - RT v^2 + (a - RTb - Pb^2)v - ab = 0
rho = W/v
```

is used in SI molar units. Every evaluated alpha bracket is positive; the
calculation stays on the principal branch above the pseudo-critical temperature.

Five choices are recorded, none selected to match a paper value:

1. `omega=0`, an explicit sensitivity control.
2. `omega=sum(Xi omega_i)`, an explicitly declared averaging rule, not a recovered
   Liang implementation.
3. The **exact effective slope of the unchanged species mixture**. On the
   positive branch, equation (2) gives `a(T)=(A-C sqrt(T))^2`, where
   `A=sum[Xi sqrt(ac_i)(1+m_i)]` and
   `C=sum[Xi sqrt(ac_i)m_i/sqrt(Tc_i)]`. At that mixture's own analytically
   calculated critical temperature, its effective slope is
   `m_eff=C sqrt(Tc)/(A-C sqrt(Tc))`. This slope is preserved when replacing
   the critical pair. Converting it to an equivalent omega only labels the
   result; no figure data enter that conversion.
4. `omega=-0.216`, the H2 input endpoint.
5. `omega=0.039`, the N2 input endpoint.

The endpoint interval is a broad sensitivity choice, **not a theorem that a
mixture's acentric factor lies between species values**. At fixed plotted pair
and this temperature, increasing omega decreases the positive alpha bracket,
attraction, and stable gas-root density. The endpoint densities therefore span
the intermediate choices at that state.

## Results and reading bounds

There are 14 shared nominal phi values from 0.6 through 1.9. The Figure 2
reading estimates remain +/-0.1 K and +/-0.05 atm. Figure 4 uses the previously
measured complete triangle extents, approximately +/-0.69 kg/m3 about the
bounding-box midpoint. A triangle's centroid differs from that midpoint;
both are retained in the CSV. These bounds describe drawing extraction,
not uncertainty reported by the authors.

| Phi | Figure 4 full vertical extent, kg/m3 | Unchanged Eq. (2), kg/m3 | Figure 2 pair + mole-average omega | Figure 2 pair + exact species slope |
| ---: | ---: | ---: | ---: | ---: |
| 0.6 | 93.335–94.722 | 93.768 | 92.170 | 92.060 |
| 1.0 | 82.681–84.074 | 83.129 | 80.756 | 80.623 |
| 1.9 | 66.333–67.726 | 66.788 | 63.042 | 62.904 |

At phi=1, the plotted pair implies `b*=33.0385 cm3/mol` and
`ac*=0.132983 Pa m6/mol2`. Mole averaging gives `omega=-0.038493` and
`a*(298)=0.0630703 Pa m6/mol2`; preserving the species slope corresponds to
`omega=-0.032083` and gives `a*(298)=0.0616944 Pa m6/mol2`.
The unchanged mixture has `b=23.5867 cm3/mol` and
`a(298)=0.0508753 Pa m6/mol2`. The larger attraction in the replacement
partly compensates its larger covolume, but not enough under these choices.

Against Figure 4's midpoint, mole averaging underpredicts density by
1.98–5.95%; retaining the exact species slope underpredicts it by 2.09–6.15%.
Neither choice overlaps any of the 14 vertical reading intervals after
propagating the Figure 2 reading rectangle. The zero-omega control also misses
all 14. At phi=1, the density ratio to the unchanged ideal-gas value is 0.9442
for mole averaging and 0.9427 for the exact species slope; the paper midpoint
ratio is 0.9749.

A supplementary sampled envelope includes the full Figure 4 horizontal marker
extent, approximately +/-0.035 in phi, and linearly interpolates the existing
Figure 2 readings. Only the 12 interior points, phi=0.7–1.8, have complete
horizontal extents inside the existing digitized range; no curve is extrapolated.
Both choices still miss all 12. This conservative envelope uses 33 phi samples
plus the nominal and marker-center positions, and corners/center of the critical
reading rectangle. It is a sampled reading sensitivity, not an author error bar
or a proof about unmeasured curve shape.

The broad endpoint omega interval gives 79.278–85.640 kg/m3 at phi=1, including
the critical reading rectangle, and overlaps Figure 4 at 13 of 14 nominal
points. At phi=1.9 it falls short by only about 0.079 kg/m3 beyond the complete
vertical triangle extent. No full horizontal assessment is made at that range
endpoint, so that small difference is not used as a universal incompatibility
claim. A density measurement at one state cannot independently identify both
attraction and covolume, and these figures do not determine a unique omega.

The stronger existing algebraic statement is unchanged: **under fixed-composition
SRK inflection and the stated species inputs, the Figure 2 covolume violates
linear species mixing**. Allowing a freely chosen pseudo-fluid temperature
function cannot repair that species-mixing identity. It can nevertheless make
some single-state densities agree, which is why this follow-up does not infer
author coefficients or claim a definitive publication error.

## Reproduction and next action

Keep the current species EOS. Do not substitute Figure 2 critical curves into
flame cases or use this diagnostic to explain all burning-speed differences.
Resolving the remaining critical-definition issue requires the author's
critical routine, constants, or original raw data. This calculation requires
no new flame job and makes no change to the earlier Figure 4 qualification.

State directory, relative to the project root:
`state/liang-hydrogen-20261020/figure24-pseudofluid/`.
The script has a read-only plan and refuses to overwrite an existing output
directory. Commands run successfully with the project analysis environment:

```powershell
& state/analysis-venv/Scripts/python.exe -B state/liang-hydrogen-20261020/figure24-pseudofluid/check_pseudofluid.py plan
& state/analysis-venv/Scripts/python.exe -B state/liang-hydrogen-20261020/figure24-pseudofluid/check_pseudofluid.py apply
```

For a rerun, specify a fresh `--output results-002` on both commands. Replaying
the independently derived effective slope with the baseline's own critical
pair reproduces its density to maximum relative difference `1.23e-15` across
all 14 states. This checks the algebraic representation, not scientific validity.

| Evidence | SHA-256 |
| --- | --- |
| `check_pseudofluid.py` | `37c9a90ba68cba0a5638403c93e07e8640b6201eaa50e38811176b18825e5c66` |
| Figure 2 audit input | `4f99b4bdbb2578d3ad20ddf50d524ebdc46b4d028a32863c738905e1bc225be6` |
| Figure 4 vector-reading input | `a62b7930fd8c1e0cef978842ab5b49a21a832034eaab6328f92c10fd545cdf99` |
| Species input | `b093c29ac896bef71f36f5fbfc1f799bdc200f259efcf9b383138076253c3346` |
| `results-001/comparison.csv` | `afe5a836cbc12a7938f2b69be98b1053fd95ba052aa072a7776fa0fbe3fc4fa2` |
| `results-001/horizontal-reading-envelope.csv` | `33e4c0833b5870abfbd47b04a276f1d011dc40a7e0de75badff3d714e6e72f62` |
| `results-001/summary.json` | `ddb26d9cabae0ddf4ac101c1c4d1f0b329e68cf03dfe9767afeeb2c504460942` |

The summary records the script and imported helper hashes, assumptions, reading
bounds, and overlap counts. `artifact-manifest.json` hashes every generated
result file. No source coefficient was fitted, and no solver, model, case,
remote state, or Git commit was changed by this audit.
