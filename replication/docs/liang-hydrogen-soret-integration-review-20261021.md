# Hydrogen author-pair Soret integration review

Research record: 21 October 2026, Asia/Shanghai. State: reviewed, not implemented
or run by this audit. Inspected source commit:
`d0cbc70ff405d7e5a78b1029b74c3d1bdc4c90f2`.

**Recommendation:** add an optional author-collision lookup to the existing
published-manual light-species coefficient, keeping hydrogen binary diffusion
and all no-Soret paths unchanged. This is a bounded H2 Case 1/3/4/5 diagnostic,
not evidence of Liang's unstated Soret settings. The
[historical sign review](liang-legacy-soret-implementation-review-20261021.md)
remains its source convention; do not reopen the sign choice through flame fitting.

## Smallest implementation boundary

[`StagedTransport.h`](../development/cantera-liang/StagedTransport.h) already
owns the manual coefficient, species selection, mixture diffusivity, density
and mass projection. Replace only its collision-ratio selection with a protected
virtual hook taking species indices and temperature. Its default should return
the current [`LightSpeciesSoret.h`](../development/cantera-liang/LightSpeciesSoret.h)
degree-six reduced-temperature fallback, preserving the methane diagnostic.

Override that hook in
[`hydrogen::Transport`](../development/liang-hydrogen/HydrogenTransport.h): use
the author actual-temperature polynomial for an available pair, otherwise call
the base fallback. Resolve species indices once and store an unordered-pair
lookup. Do not install these polynomials into Cantera's global collision arrays:
the existing custom coefficient can evaluate them directly without changing
viscosity, conductivity, ordinary diffusion or Cantera's other Soret closure.

Keep `pairs.txt` and its existing four-coefficient binary reader unchanged.
Preparation can generate a separate collision sidecar from the **same** pinned
author JSON: two species names followed by the four A, four B and four C
coefficients. Include its schema, source-JSON hash and file hash in a new immutable
input manifest. Validate exactly the same ten applicable unordered pairs as the
binary table, reject duplicates/unknown species/nonfinite or truncated rows, and
verify each binary row against that JSON. An explicitly selected author-Soret
mode must fail when the sidecar is absent; an absent individual author pair uses
the declared fallback. Old no-Soret input directories remain readable.

The current hydrogen driver still calls `enableSoret(false)` and writes
`Soret off`. Its explicit diagnostic option must set both `manualSoret` and the
flow flag, select `SoretCompatibleFlow` around the same energy-flow class,
and export native `soret-flux.csv`. Hydrogen inherits the supported
`liang-staged` identity and `StagedTransport` type. Do not rename the model.
Reject the current `midpoint-` combination: its custom flux override explicitly
excludes Soret. This first control should retain the existing ordinary stencil,
chemistry, alpha model, energy variant, inlet and mesh criteria.

## Source data and coefficient selection

[Burke's raw transport file](https://burke.me.columbia.edu/sites/default/files/content/tran.txt)
has 12 appended four-row pair records. Ten are usable with this 13-species
mechanism; atomic N is absent. The first row is D and the following rows are
A*, B*, C*, each ordered from constant through cubic. The
[author's explanation](https://web.stanford.edu/group/haiwanglab/FFCM1/pages/transport.html)
requires actual natural `log(T/K)` for these non-LJ collision ratios. Evaluate
each A/B/C cubic directly, without exponentiation, pressure scaling, reduced
temperature, or HTML-table column multipliers. All three ratios are dimensionless.

The existing D path is already correct:
`D[m2/s] = 1e-4 * exp(cubic(log(T/K))) * 101325/p[Pa]`.
Its internal `m_bdiff` stores `p*D`, in Pa m2/s. Use the raw file/JSON values;
the earlier audit found a material H–N2 C* transcription error in the web table.

| Collision records | Role in the light-species coefficient |
|---|---|
| H–He, H–H2, H2–He, H–Ar, H–O2, H–N2, H2–N2 | Seven available heteropair overrides |
| O–O2 | No direct light-species term; existing ordinary D remains active |
| H2–H2, N2–N2 | Self terms vanish because the molecular weights are equal |
| N–H2, N–N2 | Excluded: N is not a mechanism species |
| H2–O2, H–H2O and other unlisted pairs | Existing fixed legacy collision fallback |

Only H, H2 and He satisfy the current `W<5 kg/kmol` selection. H2/air has zero
He/Ar elemental abundance, so their pair terms are dormant in these flames;
retain their source records and test them with synthetic frozen states.
The symmetric A/B/C lookup must not carry the sign. The existing pair-factor
function uses output-species minus partner molecular weight; it gives opposite
signs when the output species is exchanged. Heavy-species direct theta stays
zero, with the final mass projection affecting all species.

No physical validity interval is stated for the author fits. The 300–3500 K
thermochemical intersection/legacy preprocessing interval is not such a claim.
Record minimum/maximum temperatures actually evaluated. The 298 K inlet is
slightly outside that old refitting interval; its author-fit validity is unknown.
Do not clamp A/B/C or force a Soret sign to obtain convergence.

## Dmix and preservation of the baseline

Use the existing virtual `getMixDiffCoeffs`, not a second LJ-only coefficient:
the manual formula multiplies theta by the same mole-gradient mixture
diffusivity used for ordinary transport. For physical compositions,
`Dkm=(1-Yk)/sum(j!=k,Xj/Dkj)`. In Cases 1/3/4 it consumes the existing author
binary overrides; in Case 5 it consumes those overrides with the existing
Takahashi factors. `updateDiff_T` already reaches both paths through virtual
dispatch. Applying Takahashi to A/B/C as well has no source support.

Keep the current projection:
`Uk=rho*Dkm*(Wk/Wbar)*theta_k`, then `DTk=Uk-Yk*sum(U)`.
Output is kg/(m s); Flow1D uses `-DTk*grad(log(T))` without another density.
The Case 5 use of corrected Dmix and physical SRK density is an explicitly
labelled dense thermal-diffusion assumption, not a validated extension of Burke.
At an identical nonideal T,p,X, Case 3 and Case 4 must return the same DT because
the conductivity stage is not used in this coefficient. Case 5 may differ.

With Soret off, the new lookup must never be called. Optional collision inputs
must not alter the binary table, transport caches or species data. Preserve
ordinary-property parity before interpreting any flame difference. Independently
verify pure/absent-species behavior; normalized physical states are the reference
for these checks, separate from the existing projection of Newton iterates.

## Checks before the bounded controls

1. Independently parse the raw appendix and compare all ten applicable records
   with the emitted sidecar. Exercise reversed names, duplicate records, unknown
   species, missing/malformed sidecars and an explicitly empty LJ control.
2. Evaluate A/B/C at 298, 1000 and 3000 K against independent raw-coefficient
   arithmetic. Use H–N2 to catch the HTML error and actual/reduced-T confusion.
   Reuse the prior frozen H2/N2 fixture at 1000 K: A=1.1610624993342713,
   B=1.1396282365252597, C=0.9305418868166405, and
   `theta/(XH2*XN2)=-0.3986995320795152` for weights 2.016/28.014.
3. Check author-pair reversal, two-light-species H/H2 ordering, self terms,
   dormant He pairs, absent-light limits and unlisted H2/O2 fallback. Assert
   that all ordinary D, viscosity and conductivity values are unchanged by
   selecting the new collision data, with Soret off and on at frozen states.
4. Reconstruct Dmix from the returned binary matrix in Cases 1/3/4/5, then
   independently reconstruct raw U and projected DT. Require zero summed DT,
   dilute ideal pressure independence and Case 3/4 parity at identical state.
   Test Case 5 projection after scaling raw U, not the already projected DT.
5. Exercise native Flow1D and the actual selected total-enthalpy path: zero
   thermal flux for uniform T, gradient reversal, zero summed mass flux,
   hotward binary fixture, saved Soret flag and native flux decomposition.
   Reuse `SoretCompatibleFlow` export instead of a no-Soret energy reconstruction.
6. Recheck a no-Soret baseline with the new executable, then compare paired
   on/off pilots with identical inputs and mesh qualification. Changing from
   fallback to author A/B/C is a separate comparison from enabling Soret.

These are proposed checks. Existing `test_pairs.cpp` covers binary/mixture
diffusion only; the shared methane `test_soret.cpp` has fallback fixtures but
does not yet qualify the hydrogen author collision extension.

## Evidence identity

The inspected implementation files equal HEAD. Hashes below describe local
bytes, including existing line endings. Immutable author inputs are under
`state/liang-hydrogen-20261020/mechanism-source/` outside public Git.

| File | SHA-256 |
|---|---|
| `HydrogenTransport.h` | `0aaa6ca64c942958b2bcda8e7bdeeceb746f83f4b7ab6b7153eb9d8adcb4bde3` |
| `LightSpeciesSoret.h` | `0424df6ddf6833742047f0e2fdd3a1d7d05527356b55d3fa835f55af5f8522ff` |
| `StagedTransport.h` | `925d890aaddfc8f6ce835bf2aba0659f051879bf2907005ae7211e0258b72259` |
| `pair-coefficients.json` | `d384019ce26d9d69c05fd97c23dfcb22f0624d3d0225e8563381456128ec8ff2` |
| `burke-2012-tran.dat` | `35c110cd2275845c4f4e4d57325cb59e4065ac7403b641cbd1cb7a3e1f6ca783` |
| `burke-2012-lj-utf8.yaml` | `3a227ac76148d4fce35b2dda1d57989bee885eb1cce37b14295e47de88729cc6` |

The new independent fixtures are in
`soret-audit/hydrogen-soret-fixtures-20261021.json`, SHA-256
`e3c80b483c125bf55e78e9d7845c20ff826ab95ddfc0215d50054460cec92f2d`.
They contain A/B/C/q for H2/N2, H/N2, H2/O2, H/O2 and H2/Ar at 298, 1000 and
2500 K, using the mechanism's exact molecular weights. The adjacent
`hydrogen-soret-fixtures.py` supports a read-only plan and `--apply` to a new
immutable output. It independently parses the raw appendix, checks all 12
A/B/C records against the JSON, and evaluates a sum of powers instead of the
implementation's Horner form. All 15 offline states completed; this is source
arithmetic verification, not physical validation of a temperature interval.

This review changed only this repository note and generated its ignored state
fixtures. No implementation, model data, scheduler jobs, or scientific
acceptance state was changed.
