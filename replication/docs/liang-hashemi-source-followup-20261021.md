# Hashemi reaction 567: pressure-node, collider and source follow-up

21 October 2026, Asia/Shanghai. State: source audit completed; correction
unresolved. No mechanism, solver or simulation was changed.

No verified author or publisher correction was recovered for
`CH2CHOO <=> CO2 + CH3`. The existing
[continuous sign audit](liang-hashemi-rate-audit-20261021.md) remains decisive:
the published two-term 100 atm aggregate is negative over
488.247846–580.129813 K, reaching −0.404614 s⁻¹ near 554.47 K.
Neither a missing pressure node, an additional reaction-header contribution,
nor a third-body interpretation supplies a justified repair.

## Pressure rows and the reaction header

The unchanged [Hashemi publisher archive](https://ars.els-cdn.com/content/image/1-s2.0-S0010218016301766-mmc2.zip)
contains 16 PLOG records for this reaction: two expressions at each of
`0.01, 0.1, 0.316, 1, 3.16, 10, 31.6, 100 atm`.
The original CHEMKIN block and converted YAML agree on the two terminal
100 atm expressions. There is no additional pressure node in this published
block that the conversion dropped.

At exactly 100 atm, the specified node's sum defines the rate. Adding a node
at another pressure would not change that endpoint value. A newly recovered
additional term at **100 atm** could change the sum, but none has been
established. Treating a different node as the 100 atm rate would alter the
model. This follows the
[pinned Cantera PLOG definition](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/kinetics/PlogRate.h#L57).

The reaction-header triplet is `A = 6.03e-3`, `b = 3.46`,
`Ea = 17420 cal/mol`. It must not be added as a third 100 atm term.
In the inspected
[`ck2yaml` branch](https://github.com/Cantera/cantera/blob/v3.2.0/interfaces/cython/cantera/ck2yaml.py#L1463),
the pressure-dependent rate is constructed from the PLOG list alone.
The reaction-header Arrhenius object is used by other reaction types;
it is not an omitted contribution to this PLOG fit.

The distinction between 100 bar and 100 atm also does not remove the problem.
100 bar is approximately 98.69 atm, between the 31.6 and 100 atm nodes.
At affected temperatures its logarithmic interpolation still requires the
negative 100 atm aggregate. The nearest-node convention above the last
pressure likewise cannot restore positivity. These are consequences of the
specified expression, not results of a flame calculation.

## Collider interpretation

The reaction is unimolecular as written. Its block contains no `M`, `(+M)`,
`LOW`, `TROE`, `SRI`, or species-efficiency entries. The converter explicitly
selects a PLOG rate rather than a third-body/falloff rate. The
[PLOG state update](https://github.com/Cantera/cantera/blob/v3.2.0/src/kinetics/PlogRate.cpp#L18)
uses temperature and total thermodynamic pressure.

A bath-gas model can affect the underlying master-equation calculation and
therefore the fitted coefficients. That is a physical applicability question;
it does not introduce an unspecified positive multiplicative collider term
into this published PLOG block. Multiplying the aggregate by a positive
concentration or efficiency would preserve its negative sign.

The original Goldsmith fit's bath-gas/energy-transfer metadata have not been
independently recovered in this follow-up. No particular collider is asserted,
and no alternate bath-gas fit is substituted.

## Author metadata and correction search

The upstream source is
[Goldsmith et al., 2015](https://doi.org/10.1021/acs.jpca.5b01088).
The publisher identifies two supporting text files, including CHEMKIN PLOG
coefficients. Its original
[rate-file link](https://pubs.acs.org/doi/suppl/10.1021/acs.jpca.5b01088/suppl_file/jp5b01088_si_001.txt)
was not accessible through the available normal retrieval path.
The publisher article endpoint returned HTTP 403, and a public Figshare
metadata search for the resource DOI also returned HTTP 403.
No original rate-file content or hash is claimed from these attempts.

The [author's Brown publication record](https://vivo.brown.edu/display/cfgoldsm)
links the same article DOI. Searches of the exact DOI/title with correction
and erratum terms, the author record, and the original
[Cantera issue discussion](https://github.com/Cantera/cantera-website/issues/77)
did not produce corrected coefficients. The issue documents the negative sum
and closes through a documentation update; it does not record an author repair.
This is a bounded search result, not proof that no unpublished correction exists.

The copied `400–2100 K` annotation in the linked user discussion remains
unverified against Goldsmith's original file. Even if that annotation were
confirmed, it would include the full negative interval and would not resolve
the present defect. The Hashemi block itself prints no temperature domain.
A restriction excluding 488–580 K would still leave a 298 K flame without a
qualified rate throughout its preheat zone unless an authored alternative
were supplied there.

The previously audited duplicate inventory already compared the channel in
both directions across all 631 reaction records. No matching positive
duplicate exists. Different products from the same CH2CHOO reactant cannot
be combined into this channel. That result was not recomputed or weakened
by this follow-up.

## Evidence and decision

`state/liang-hydrogen-20261020/hashemi-source-followup/source-inventory.json`
preserves all 16 raw pressure rows, node inventory, access failures and hashes
of the mechanism, converted YAML and inspected Cantera source.
The numerical ASCII fields were inspected with a byte-preserving Latin-1
decode after the machine-default GBK decode failed on a source comment.
No file was transcoded or rewritten.

Original mechanism SHA-256:
`20996e0d5ac1163fb28d16f7f1e343a55d64f0d7a05e6f4eaeabc40b1a9d3a7f`.
Converted YAML SHA-256:
`8ca71928cee58e08a4dc8da538fc667675845a3673218d9f7b74e097fd5d96da`.

The exact published Hashemi curve remains blocked. A defensible new revision
requires an authored corrected fit or original positive channel-rate data
with pressure, temperature, collider and fitting metadata. No clipping,
deletion, coefficient adjustment, alternative pressure assignment or
parser bypass is justified by the evidence obtained here.
