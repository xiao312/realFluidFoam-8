# Liang property comparison, 19 October 2026

The compiled SRK density follows Liang Figure 1(a). The conductivity and
mixture critical-point checks expose unresolved model differences. These
results do not yet qualify Liang Figure 8(a), Cases 2–5.

## Implemented and tested

The new `development/liang-properties` module contains a reusable C++11
Ely–Hanley conductivity kernel, a compiled OpenFOAM property probe, an
immutable NIST fetcher, implementation checks, and original-scale PDF overlays.
The probe calls the fork's SRK density/coefficient methods. It assembles the
fixed-composition geometric mixture coefficients explicitly for the critical
calculation. The existing registered library already contains SRK, nonideal
mixture enthalpy, and Takahashi diffusion; it did not contain Ely–Hanley.

Job **124887485**, source **e208396bdba48592aacbf6bb9a1c41b8eca3d9bb**,
passed 901 finite oxygen states and 282 critical-point states. The largest
normalized first/second pressure derivative residual is **1.81e-14**.
Reference-fluid conductivity limits, artificial species splitting, invalid
inputs and pure-fluid critical recovery passed. The library remains build
124657926. [The record](liang-properties-20261019.json) pins binary, species,
image, source, NIST and figure hashes.

Three short build attempts failed before the first successful job 124886757:
one template include-order error and two linker attempts that selected stock
OpenFOAM `libspecie` before the fork. The probe now links the exact qualified
fork library path. The final diagnostic variant ran in a new immutable job.
No running flame binary or library was changed by this property work.

## Figure 1: oxygen at 100 atm

Density agrees visually with the paper model. Against independently fetched
current NIST data over 300–1000 K, its RMS relative error is **0.622%** and
maximum absolute relative error **1.370%**. These are errors against today's
NIST reference model, not errors against the paper's triangular markers.

The default conductivity uses methane reference mass per corresponding molar
volume: `rho_ref = rho_mix * h * W_ref/W_mix`. Original NBS TRAPP code confirms
that density conversion. This explicit-shape-factor Ely–Hanley variant gives
0.03205 W/(m K) at 200 K and 0.03407 at 300 K. Its 300–1000 K RMS error against
current NIST is **9.264%**. Exact equivalence to Liang's variant is not established.

A separately labelled diagnostic omits `W_ref/W_mix`, as in Cantera 3.2's
current high-pressure conductivity source. This is evaluated by our new kernel,
not by running Cantera nonideal flames. It gives 0.04895 at 200 K and 0.04007 at
300 K and follows the paper model much more closely. That is evidence of
sensitivity to the convention, **not proof of Liang's source code or a reason
to change the default silently**. Both curves remain in the comparison.

Below 200 K, the author NASA polynomial is explicitly extrapolated for the
internal conductivity contribution. These points are marked unqualified; the
probe neither clips the requested temperature nor changes the input's bound.
The complete 1983 conductivity article and Liang's implementation/input deck
would help resolve the remaining variant choices.

## Figure 2: fixed-composition SRK critical points

The [subsequent critical-point audit](liang-critical-audit-20261019.md) confirms
the native results independently. It also shows that the paper's paired curves
imply covolumes outside the H2/O2/N2 species bounds and opposite composition
trends. The disagreement remains unresolved; no EOS coefficients were changed.

The paper defines a P–v inflection. Our calculation satisfies that definition
for the fork's coefficients and assumed 21/79 molar O2/N2 air, but does not
match the published curves. At phi=1:

| Mixture | Computed Tc (K) | Paper Tc (K) | Computed Pc (atm) | Paper Pc (atm) |
|---|---:|---:|---:|---:|
| H2/air | 105.105 | 98.12 | 31.681 | 21.11 |
| CH4/air | 136.646 | 138.19 | 37.147 | 40.61 |

Paper values come from vector paths with calibrated dual axes; estimated
calibration uncertainties are 0.1 K and 0.05 atm. They are not author raw data.
No species parameters were fitted. This construction is a pseudocritical
inflection, not the full multicomponent phase-stability critical locus.

## Gate before staged reacting flames

The kernel and property checks are safe to merge as isolated development tools.
They are not yet connected to the running reacting solver. Independent
EOS/caloric/conductivity/diffusion selection still needs a runtime adapter and
qualification. Cases 2–5 must change only the intended component, including a
common dilute diffusion base for the Case 4–5 comparison.

The current energy equation uses an enthalpy-gradient identity with
pure-species enthalpies; the chemistry ODE also forms heat capacity and
reaction enthalpy from pure-species sums. These need mixture-consistent checks
before claiming Liang's nonideal enthalpy formulation. The next source change
must handle conservative Fourier heat flux, partial mixture enthalpies, and
chemistry temperature/Jacobian consistency together with regression evidence.
An unchanged SRK/Chung flame must not be relabelled as Liang Case 4 or Case 5.

Figure output: `output/liang-figures-1-2-20261019-v6/liang-figures-1-2.pdf` in
the operator workspace. Both originals, captions and source typography remain
at publication scale; new data have explicit legends. The Lark comparison
entry uses the same two comparison images.

