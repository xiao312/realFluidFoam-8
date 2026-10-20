# Hashemi reaction 567: a negative aggregate, not a missing duplicate

Research snapshot: 2026-10-21, Asia/Shanghai. The exact Hashemi-2016 release
cannot pass a nonnegative-rate check over 298-3500 K at 100 atm.
Reaction 567, `CH2CHOO <=> CO2 + CH3`, is the only matching channel in either
direction among all 631 reaction records. Its two 100-atm PLOG terms sum to a
negative rate between 488.247846 and 580.129813 K. There is no separate positive
duplicate to include.

An exact signed-Arrhenius representation is algebraically possible at this
fixed pressure, but it preserves the negative aggregate. It therefore cannot
provide the same qualification obtained for the HP-Mech signed-term conversion.
No solver, mechanism input or job was changed in this audit.

## Exact source and duplicate inventory

The mechanism is the supplement to
[Hashemi et al., High-pressure oxidation of methane](https://doi.org/10.1016/j.combustflame.2016.07.016),
with header release date 2016-07-18, 68 species and 631 reactions.
The publisher's [mechanism ZIP](https://ars.els-cdn.com/content/image/1-s2.0-S0010218016301766-mmc2.zip)
was downloaded again on 21 October 2026. Its SHA256 remains
`27ff94441f53f9742e056930e1d57bf3e4c231656de127b1aeaa52084d1986ac`,
identical to the earlier campaign acquisition.

The raw `mech.inp` SHA256 is
`20996e0d5ac1163fb28d16f7f1e343a55d64f0d7a05e6f4eaeabc40b1a9d3a7f`.
The strict-conversion YAML SHA256 is
`8ca71928cee58e08a4dc8da538fc667675845a3673218d9f7b74e097fd5d96da`.
Reading its YAML data directly avoids attempting to load the already-invalid
PLOG expression into a kinetics evaluator. This is source inspection, not a
bypass used to produce simulation data.

The inventory compared both ordered reactant/product maps and signed net
stoichiometry, including reversed orientation and omission of an unchanged
third-body label. Only reaction 567 matches. It is reversible and is not marked
duplicate. Its raw block starts at `mech.inp` line 3041. Neighboring reaction
566 is `CH2CHOO <=> CO + CH3O`: its different products prevent combining it
with 567 as if it were another fit term for the same channel.

The complete unimolecular CH2CHOO inventory is retained in the evidence JSON:
reverse channels 275 and 304, and forward channels 560-567. Channels that
consume the same reactant but produce different species do not supply a
missing positive rate for `CO2 + CH3`.

## Analytical sign check

The source header uses mol, cm, seconds and cal/mol. For this unimolecular
reaction, the resulting rate coefficient is in s-1. At exactly 100 atm:

```text
kminus(T) = -2510 * T^1.41 * exp(-14420/(Rcal*T))
kplus(T)  = 4.05e-9 * T^5.14 * exp(-10480/(Rcal*T))
k(T)      = kminus(T) + kplus(T)
Rcal      = 8.31446261815324/4.184 cal/(mol K)
```

The negative sign is part of the supplied coefficient. The two PLOG records at
the same pressure are already additive, not alternatives. Define

```text
q(T) = ln[kplus(T)/abs(kminus(T))]
     = ln(4.05e-9/2510) + 3.73*ln(T) + 3940/(Rcal*T)
q'(T) = [3.73*T - 3940/Rcal]/T^2
```

For positive temperature, q decreases until 531.550928 K and increases
afterwards. This gives a unique global minimum:
`qmin = -0.0138566700`, or `kplus/abs(kminus) = 0.986238892`.
Both q(298 K) and q(3500 K) are positive. There are therefore exactly two
zero crossings inside the audit interval, with a negative aggregate between
them. The crossings were located by bisection on the analytical q function;
the sign conclusion does not depend on a finite temperature grid.

| Quantity | Result |
| --- | ---: |
| Lower zero crossing | 488.247845882 K |
| Upper zero crossing | 580.129812615 K |
| Most negative rate | -0.404613687 s-1 |
| Temperature of most negative rate | 554.470656706 K |
| k at 298 K | 0.000230059 s-1 |
| k at 500 K | -0.053561302 s-1 |
| k at 600 K | 1.451642 s-1 |
| k at 1000 K | 24510.229430 s-1 |

The rate minimum was located from the derivative of the two-term rate.
It differs from the minimum of their ratio. The modest 1.38% ratio deficit
describes cancellation between terms; it does not establish a rounding repair
or identify a replacement coefficient.

Five 100-atm PLOG groups in this mechanism contain a negative term.
Applying the same continuous-interval proof to each gives:

| Reaction | Channel | Minimum positive/negative magnitude ratio, 298-3500 K | Sign |
| --- | --- | ---: | --- |
| 285 | C2H3 + CH2O <=> C2H4 + HCO | 1.755292 | Positive |
| 468 | CH2CHO + H <=> CH3 + HCO | 1.704840 | Positive |
| 566 | CH2CHOO <=> CO + CH3O | 1.009170 | Positive |
| 567 | CH2CHOO <=> CO2 + CH3 | 0.986239 | Negative interval |
| 593 | OCHCO <=> HCO + CO | 1.755860 | Positive |

This confirms that a negative individual Arrhenius term is not itself the
failure criterion. The aggregate is the relevant quantity. It also rules out
the nearby negative term in reaction 566 as a second blocked group at this
pressure. These results concern the 100-atm nodes and the stated interval;
they do not qualify other pressures or extrapolated temperatures.

## What the Cantera history establishes

[Cantera website issue 77](https://github.com/Cantera/cantera-website/issues/77)
was opened on 28 May 2019 for this exact Hashemi reaction and these exact
coefficients. The maintainer identified a negative *summed* rate at 500 K,
which makes logarithmic pressure interpolation undefined. The issue was
closed in July 2020 after
[commit 7d535a4 clarified the documentation](https://github.com/Cantera/cantera-website/commit/7d535a4).
The retrieved discussion contains no corrected coefficients or author-approved
replacement mechanism. Its closed status does not mean the published fit was
repaired.

The linked
[May 2019 Cantera user discussion](https://groups.google.com/g/cantera-users/c/zy4GOvsiYVM)
shows the same channel under the name `C2H3O2` in a Konnov input. That copied
block labels its 100-atm fit as 400-2100 K with two reported error values of
40.7% and 150.7%. Those annotations are evidence about the input posted in
that thread; the original Goldsmith supplement was not independently retrieved
in this audit, so they are not treated as verified Goldsmith fit metadata.

The raw Hashemi block cites
[Goldsmith et al., JPCA 119 (2015) 7766-7779](https://doi.org/10.1021/acs.jpca.5b01088).
The publisher describes its supporting information as CHEMKIN-compatible
PLOG coefficients. Searches of the original publication records, the issue,
its linked thread and correction-related queries did not identify a verified
author correction for this channel. Direct retrieval of the original ACS
supplement was unsuccessful. The current Hashemi publisher ZIP is demonstrably
unchanged; the broader existence of an unpublished or separately distributed
correction remains unknown.

## Fixed-pressure conversion decision

At 100 atm, replacing the PLOG record by two reversible Arrhenius duplicates
with unchanged A, b and Ea can reproduce the two-term expression algebraically.
Because both duplicates would have the same equilibrium constant, their summed
forward and reverse mass-action contributions would also reproduce that
expression. This avoids taking a logarithm but does not make k nonnegative.

For example, at 500 K with CH2CHOO present and both products absent, the reverse
mass-action product is zero. The negative forward coefficient gives a negative
CO2 production rate. That is a direct positivity defect, not a choice of
equilibrium-constant convention. A successful parser or numerical flame solve
with signed duplicates would not remove it.

Consequently, there is no exact, everywhere nonnegative representation of this
source channel over 298-3500 K. Restricting it to temperatures outside the
negative interval would not cover a flame starting at 298 K. Clipping, deleting
the channel, altering coefficients, substituting a different pressure node, or
changing its products would each change the kinetic model.

The source-supported next step is to obtain corrected coefficients or the
original positive channel-rate data with their validity range and provenance.
Any such input must be kept as a distinct mechanism revision and checked
before a new flame comparison. Until then, the exact Hashemi-2016 curve remains
blocked; the usable USC, HP and GRI controls can proceed independently.

## Reproduction and evidence

Local evidence is under
`state/liang-hydrogen-20261020/hashemi-rate-audit/`.
`audit.py` pins both source hashes and supports read-only planning:

```text
python -B audit.py plan ../figure8b-sources new-results
python -B audit.py apply ../figure8b-sources new-results
```

Both operations completed using the project's Cantera 3.2 environment and
its ruamel.yaml dependency. Only YAML parsing, scalar analysis and file writes
were used; no kinetics evaluator, integrator or scheduler job ran.
`results/audit.json` preserves the complete target block, duplicate inventory,
all five sign certificates and exact script/input hashes.
`results/rate-100atm.csv` contains an additional 1 K sampled curve; the
continuous sign proof remains the qualification evidence.
`issue-77.json` and `issue-77-comments.json` archive the public issue response.
`publisher-mmc2-20261021.zip` preserves the freshly checked publisher archive.
