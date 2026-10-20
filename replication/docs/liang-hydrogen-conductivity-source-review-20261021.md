# Rich-hydrogen conductivity source review, 21 October 2026

**Liang's hydrogen-specific mixing and conformal-mapping modification remains
unresolved. No additional source found in this bounded review specifies it.**
A published dilute-mixture rule supplies one additional fixed-coefficient check,
but its evaluated change has the wrong sign in the fresh mixture and is small
through the sampled flame. It does not justify another presumed Liang model.

Reviewed at 04:02 Asia/Shanghai, against repository revision
`ae10e5c32ea9e794a2ab584f1f03eb72af4788cd`. This was a source review and local
frozen-property calculation. No flame was solved, no remote files were written,
and no model, mechanism or input was changed.

## What the source trail establishes

The [journal article](https://doi.org/10.1016/j.proci.2018.06.070) names a rich-H2
modification without its equations. Chapter 8 of the
[author's dissertation](http://imgsvr.riss4u.net/ddod8/201812/14998/128/14998128.pdf)
does not add them. The full chapter and absence of embedded attachments were
already checked in the [dissertation audit](liang-conductivity-source-audit-20261021.md).
That audit also establishes the distinct conductivity-ratio definitions and
curve values in journal Figure 6 and thesis Figure 8-5. A label inversion alone
does not reconcile either curve with our model.

The [earlier conductivity audit](liang-hydrogen-conductivity-audit-20261020.md)
already covers references 5–8 and 10, standard Ely–Hanley, the NBS TRAPP program,
fixed-volume derivatives, molecular-weight conversion of reference density,
dilute mixing variants and the normal-H2 quantum/reference correlation.
Those are not new hypotheses in this review. In particular, the original
coupled mapping, original methane constants and noncorrespondence correction
have already undergone property checks; substituting them did not close the gap.

Three additional lead families were checked:

| Lead | Accessible primary evidence | What it does and does not provide |
| --- | --- | --- |
| Weiyu Li's related work | Princeton's [2017 exam abstract](https://mae.princeton.edu/sites/default/files/Weiyu%20Li%20-%20abstract%20-Flame%20dynamics%20in%20supercritical%20condition.pdf) and [2019 degree record](https://mae.princeton.edu/sites/g/files/toruqf7696/files/2019%20-%20Class%20Day%20-%20Introduction%20of%20Graduates.pdf) | Confirms the staged supercritical-flame study and MSE thesis title. Repeated exact-title/author searches did not locate a public full thesis, implementation or coefficient supplement. The abstract gives no transport equations. |
| Bai, Xin Zhang and Hao Zhao, 2025 | [Publisher abstract, DOI 10.1016/j.combustflame.2025.114144](https://www.sciencedirect.com/science/article/pii/S0010218025001828) | Reports hydrogen flame-speed overprediction by its RK–EH/Takahashi comparator and identifies mixture conductivity as a weakness. This is an independent comparator, not a recovered implementation of Liang's modification. Full text, comparator code and coefficient inputs were not obtained from the publisher or author-page searches. |
| Improved conformal mixing for unequal molecular sizes | [Ely's publication list](https://inside.mines.edu/fs_home/jely/Publications.htm) and [Huber and Ely's 1990 author-uploaded abstract](https://www.researchgate.net/publication/226622999_Extension_of_an_improved_one-fluid_conformal_solution_theory_to_real_fluid_mixtures_with_large_size_differences) | The latter explicitly concerns a Helmholtz-free-energy correction and thermodynamic mixture calculations. Its title is insufficient evidence for an H2 conductivity replacement. No direct link to Liang's transport implementation was found. |

The [Zhao group publication page](https://neec-pku.github.io/ZHAOHAO/publication.html)
provided the complete [Bai et al. 2022 paper](https://neec-pku.github.io/ZHAOHAO/pubs/J23.pdf).
That paper studies hydrogen oxidation with the virial equation of state; it does
not provide a flame conductivity model. No code or hidden download route was
inferred from its filenames. Publisher errors and missing open copies were
treated as retrieval limits, not proof that the material does not exist.

## One additional explicit dilute-mixture check

The [author-uploaded manuscript of Zhukov and Pätz](https://www.researchgate.net/publication/311803060_On_Thermal_Conductivity_of_Gas_Mixtures_Containing_Hydrogen),
published as [Heat and Mass Transfer 53, 2219–2222](https://doi.org/10.1007/s00231-016-1952-9),
gives the following Mason–Saxena variant in equation 5:

\[
\lambda_{MS}=\sum_i\frac{x_i\lambda_i}
 {x_i+\sum_{j\ne i}x_jG_{ij}},\qquad
G_{ij}=1.065\frac{[1+\sqrt{\mu_i/\mu_j}(M_j/M_i)^{1/4}]^2}
 {\sqrt{8(1+M_i/M_j)}}.
\]

Here \(\lambda_i\) and \(\mu_i\) are pure-species dilute properties at the same
temperature; molecular weights must use consistent units. The factor 1.065
applies only to unlike-pair terms. Keeping the diagonal equal to one preserves
the pure-species limit. This is distinct from our previous 1.0-factor Wilke
diagnostic. The source compares H2/O2 mixtures at 1 atm and 323/373 K. It does not
provide Liang's dense-mixture mapping or establish a 100-atm flame model.

For reference, the current Mathur/Cantera dilute mixture rule is

\[
\lambda_M=\tfrac12\left[\sum_i x_i\lambda_i+
 \left(\sum_i x_i/\lambda_i\right)^{-1}\right].
\]

Using identical pure-species properties from our existing Burke input, stock
Cantera 3.2.0 and frozen fresh H2:O2:N2 mole proportions \(2\phi:1:3.76\):

| T, K | Phi | Mathur, W/(m K) | Mason–Saxena, W/(m K) | MS/Mathur |
| --- | ---: | ---: | ---: | ---: |
| 300 | 1.0 | 0.05470295 | 0.05539050 | 1.012569 |
| 300 | 1.4 | 0.06234042 | 0.06442021 | 1.033362 |
| 800 | 1.0 | 0.11285708 | 0.11485028 | 1.017661 |
| 800 | 1.4 | 0.12776195 | 0.13249643 | 1.037057 |

The same check used the saved phi=1.4, 100-atm manual-Soret Case 3 profile,
job **125091785**, to test whether changing composition reverses that finding.
Mass fractions were interpolated at the stated temperatures and converted by
Cantera to mole fractions. Both conductivity calculations used that identical
state; no equilibrium or flame integration occurred.

| T, K | MS/Mathur at saved flame composition |
| --- | ---: |
| 300 | 1.028345 |
| 800 | 0.996469 |
| 1200 | 0.996570 |
| 1500 | 0.998695 |
| 2000 | 1.002721 |

All reported temperatures are inside the profile's 298–2301.57 K range.
Trace negative mass fractions have magnitude below 1.2e-15; Cantera's composition
setter normalizes its nonnegative composition. These figures isolate the
dilute mixing rule. No dense increment was added, and a property ratio is not
a quantitative prediction of flame-speed response. The result does not support
this variant as a sufficient explanation of the conductivity discrepancy.

## What is still needed to reproduce the named modification

An implementation specification must identify all of the following:

1. The pure-H2 conductivity/reference model and treatment of other species,
   especially H, H2O, HO2 and H2O2.
2. The exact unlike-pair and mixture rules, coefficients, molecular-weight
   weighting and any composition-dependent activation criterion for rich H2.
3. Whether the modified mapping acts on the full translational contribution,
   only its dense residual, the internal contribution, or more than one term.
4. The reference fluid, mapped temperature and density equations, use of mass
   versus molar density, derivative convention and clipping/domain limits.
5. Whether Case 1 and Cases 4/5 share the same zero-density limit. A nonideal
   property option that also changes dilute mixing can alter a flame even as
   pressure tends to zero.
6. The states used for Figure 6 ratios: common composition or each flame's own
   composition, numerator/denominator source version, and diffusivity definition.

Neither matching one Soret-enabled Case 3 point nor reversing a figure label
specifies these inputs. Soret is a separate transport control and cannot be
enabled selectively to make individual case labels agree without source support.

The next defensible conductivity work is an independent property benchmark:
test the existing Mathur, full EH, dense-increment EH and fixed 1.065 rule against
the same dilute H2/O2 compositions before any further flame sweep. The original
[Gray, Holland and Maczek measurements](https://pubs.rsc.org/en/Content/ArticleLanding/1969/TF/TF9696501032)
cover six binary systems at 50 and 100 degrees C, including H2/O2. The publisher
abstract was obtained; its numerical tables and experimental uncertainty have
not yet been recovered. Until those are available, this is a planned benchmark,
not a completed validation. A successful dilute check would still leave dense
mixture validation and Liang's exact mapping unresolved. No factor should be
selected or adjusted by agreement with Liang's flame speeds.

## Reproduction and evidence

The existing files read by the new calculations are under
`state/liang-hydrogen-20261020/` relative to the operator project root:

| Input | SHA-256 |
| --- | --- |
| `inputs-pairs/ideal.yaml` | `1ae5fe0b232390d6434764bdc2002e1a2da9f1606f11473909ebb8476c483076` |
| `hydrogen-soret-rich-manifest.json` | `ed81ed0c73aaca62906b526913a2a26916fcef4d30a98d013301066c9f75275b` |
| `snapshot-hydrogen-soret-0355/jobs/125091785/result/profile.csv` | `9941e8e18fef6ca720c9d919551cbb286eb7f1fd9e6dfcfa075e750155a2c5bb` |

The following read-only Python fragment reproduces the fresh-mixture rows with
the existing equilibrium virtual environment. Supply the mechanism path as the
first argument. No file is created; the temperature and phi loops define all
reported fresh states.

```python
import sys
import cantera as ct
import numpy as np

gas = ct.Solution(sys.argv[1])
mass_ratio = gas.molecular_weights[:, None] / gas.molecular_weights[None, :]
for temperature in (300.0, 800.0):
    gas.TP = temperature, ct.one_atm
    viscosity = gas.species_viscosities.copy()
    pure = []
    for species in gas.species_names:
        gas.TPX = temperature, ct.one_atm, {species: 1.0}
        pure.append(gas.thermal_conductivity)
    factor = (1 + np.sqrt(viscosity[:, None] / viscosity[None, :])
              / mass_ratio**0.25)**2 / np.sqrt(8 * (1 + mass_ratio))
    factor *= 1.065
    np.fill_diagonal(factor, 1.0)
    for phi in (1.0, 1.4):
        gas.TPX = temperature, ct.one_atm, {"H2": 2 * phi, "O2": 1, "N2": 3.76}
        reference = gas.thermal_conductivity
        estimate = np.sum(gas.X * np.array(pure) / (factor @ gas.X))
        print(temperature, phi, reference, estimate, estimate / reference)
```

For the profile table, replace the fresh composition with
`gas.TPY = temperature, ct.one_atm, interpolated_mass_fractions`, then retain
`gas.X` before evaluating pure-species states. The coefficients depend only on
temperature in this dilute comparison. Sample each `Y_<species>` column against
`T_K`; do not extrapolate outside the original profile. Source/model evidence
for earlier checks remains in the linked audits. This review added only this
note and retained no new downloaded copyrighted files in Git.
