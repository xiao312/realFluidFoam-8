# SRK departures and chemistry coupling: source check

21 October 2026, Asia/Shanghai. Tested interpretation, not paper acceptance.

No new missing enthalpy or heat-capacity term was identified. The references
support the existing consistent SRK departure equation. They describe several
different chemistry and species-enthalpy conventions, so a shared citation
cannot identify Liang's implementation. The completed concentration and Cp-only
controls do not close the hydrogen Case 3 discrepancy.

This note extends the [energy follow-up](liang-energy-followup-20261021.md)
and [conservation audit](liang-energy-conservation-audit-20261021.md).
No coefficients, models or running jobs were changed.

## Departure identities

Let `a=a(T,X)`, `b=b(X)`, `v` be molar volume, and
`L=ln(1+b/v)`. At fixed composition the SRK equation is

```text
p = R*T/(v-b) - a/[v*(v+b)].
```

The mixture departure enthalpy and its constant-pressure derivative are

```text
H_R = p*v - R*T + (T*a_T-a)*L/b

Cp_R = p*v_T - R + T*a_TT*L/b
       - (T*a_T-a)*v_T/[v*(v+b)],
v_T = -p_T/p_v.
```

These are exactly the expressions in
[SrkKernel.h](../development/cantera-liang/SrkKernel.h).
The numerically rearranged first two enthalpy terms,
`R*T*b/(v-b)-a/(v+b)`, equal `p*v-R*T`; no pressure-work term was lost.
Using the EOS again reduces the heat-capacity expression to

```text
Cp_R = T*a_TT*L/b - T*p_T^2/p_v - R.
```

This follows from the general departure integral in reference 5, Eqs.11–13.
That paper itself uses Peng–Robinson: its EOS-specific closed forms must not be
copied into SRK. Reference 10's Eq.71 gives the equivalent SRK enthalpy in
mass-specific notation.
[Pons et al.](https://doi.org/10.1080/13647830802368821),
[Giovangigli et al.](https://www.cmap.polytechnique.fr/~giovangi/688.pdf)

Thus an extra Cp term or pressure-work source is not supported. This algebra
holds on a smooth alpha branch; the original mixing rule's alpha-crossing
discontinuity remains the separate, already-tested limitation.

## Partial versus pure enthalpies

Reference 6 explicitly identifies its species values as partial-mass enthalpies.
Its convection term is `m*sum(Y_k*d hbar_k/dx)`. For a differentiable extensive
mixture at constant pressure,

```text
h = sum(Y_k*hbar_k)
dh = Cp*dT + sum(hbar_k*dY_k)
sum(Y_k*d hbar_k) = Cp*dT.
```

Consequently its temperature and total-enthalpy forms are equivalent when the
same partial enthalpies are used throughout. Reference 7 adopts that framework.
This is consistent with our partial-enthalpy implementation.
[Huo et al., Eq.4 and its definitions](https://yang.gatech.edu/publications/Journal/C%26F%20%282014%2C%20Huo%29%20-%20S%20curve.pdf),
[Wang et al., theoretical framework](https://doi.org/10.1080/00102202.2014.973955)

Reference 5's Appendix A also calculates mixture-dependent partial enthalpies,
including partial volumes and cross-attraction derivatives. Reference 8 instead
evaluates individual pure-species departures and describes replacing mixture
enthalpy by their mass-weighted sum as an approximation. Its warning against
that approximation is not a general failure of the partial-enthalpy identity.
The existing pure-flux and pure-temperature diagnostics already isolate this
definition difference.
[Pons et al., Eq.29](https://doi.org/10.1080/13647830802368821),
[Jorda Juanos and Sirignano, Eqs.5/8 and Section 3](https://sirignano.eng.uci.edu/theme/pdfs/39.pdf)

## Chemistry conventions are separate model choices

Reference 10, Section 4.4, defines:

| Source model | Mass-action concentration | Reverse equilibrium |
|---|---|---|
| PG | `X_k*p/(R*T)` | Ideal standard-state thermochemistry |
| PG-HP | Actual `rho*Y_k/W_k` | Same ideal equilibrium law |
| Hybrid | Actual concentration in forward rates | Nonideal correction only through equilibrium |
| Nonideal | Activity in both forward and reverse mass action | Symmetric thermodynamic formulation |

Our pressure adapter implements PG. The actual-concentration control implements
PG-HP. Reference 10 explicitly rejects the asymmetric Hybrid construction as
thermodynamically inconsistent. It does not establish that Liang used the fully
nonideal formulation merely because Liang cites that paper.
[Giovangigli et al., Eqs.56–59](https://www.cmap.polytechnique.fr/~giovangi/688.pdf)

The completed matched-energy controls give:

| phi | Pressure-based Case 3, cm/s | Actual-concentration Case 3, cm/s | Change |
|---|---:|---:|---:|
| 1.10 | 56.580722 | 56.261328 | -0.5645% |
| 1.40 | 75.567697 | 75.196517 | -0.4912% |

These use C4 alpha and the author pair table. They also alter third-body/falloff
concentrations, not just elementary mass action. Their exact jobs and passed
six-state rate check are in the
[checkpoint](liang-overnight-checkpoint-20261021.md).
The effect is insufficient to explain the paper Case 3 gap.

A future full activity control must explicitly define collision/falloff
concentrations too. Cantera 3.2 separates activity concentrations used in
mass action from physical concentrations used for third bodies.
Simply setting `fugacityKinetics=true` also retains physical SRK third-body
concentrations in the standard kinetic evaluator. It is not equivalent to the
earlier frozen activity-only probe that held prefactors fixed.
[BulkKinetics.cpp](https://github.com/Cantera/cantera/blob/v3.2.0/src/kinetics/BulkKinetics.cpp)

## PREMIX does not establish Liang's modified residual

The author-written 1998 PREMIX manual gives an ideal-gas temperature equation
with mixture Cp in convection, species Cp in diffusive enthalpy transport,
and species enthalpy in the chemical term. A freely propagating adiabatic flame
solves the energy equation; prescribing its temperature profile defines a
different calculation. Its units are internally CGS.
[PREMIX manual, pp.11–12](https://ae.iitm.ac.in/~amitk/AS5640/PREMIX.pdf)

The retained public PREMIX source calls `CKWYP(P,T,Y)` independently of its
midpoint density evaluation, then calls `CKHML`, `CKCPBS`, and `CKCPMS`.
This explains a plausible pressure-based chemistry lineage. It does not prove
which calls Liang replaced, and the mirror is not Liang's modified source.
See the pinned source and limitations in the
[transport-lineage audit](liang-transport-lineage-20261020.md).

The completed Cp-only diagnostic tested the narrower interpretation of the
dissertation's heat-capacity wording. It passed ideal parity, but lowered
nonideal Case 3* speed and temperature away from its paper comparison.
At phi 1.40 the change was 76.014137 to 74.944278 cm/s and
2302.931 to 2298.509 K. It therefore supplies no supported reason to modify
the consistent baseline.

The remaining implementation uncertainty is the author's exact stage-switch
logic and nonideal residual. Adding an independently valid term that the current
equation already contains would double count it. The comparisons above constrain
that uncertainty; they do not prove an error in the published implementation.

## Evidence

Read-only sources were the current `SrkKernel.h`, `SrkPhase.h`,
`PressureChemistry.h`, `EnergyFlows.h`, Cantera v3.2.0 source, and the cached
reference 5–8/10 texts in
`state/liang-hydrogen-20261020/conductivity-sources/`.
The measured controls are immutable records under
`snapshot-concentration-0046` and `snapshot-cp-only-0131`.
No new simulation, frozen-state calculation, parameter fit or code edit was
needed for these algebraic and source-definition checks.
