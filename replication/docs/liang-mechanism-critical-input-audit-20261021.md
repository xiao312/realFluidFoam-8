# Full USC/HP nonideal inputs: critical-parameter feasibility

21 October 2026, Asia/Shanghai. Inventory tested; a full nonideal input is not
qualified or assembled.

The author mechanisms contain positive Lennard–Jones diameter and well-depth
values for every species: all 111 USC and all 92 HP species. Missing transport
numbers therefore do not prevent radical parameter estimates. They do not,
however, supply a complete measured critical-property table or the acentric
factors needed by the current SRK alpha rule. Stable-species identity mapping
and the classification of inferred values remain necessary.

## Exact meaning of reference 10's estimates

Reference 10 distinguishes stable substances, whose SRK parameters can be
obtained from physical critical states, from chemically unstable species that
cannot have a measurable pure-fluid critical state. Its Eqs.38–39 derive
estimates from an assumed Lennard–Jones interaction potential:

```text
Tc = (1.316 +/- 0.006) * epsilon/kB
vc_mass = (3.29 +/- 0.07) * NA*sigma^3 / W
a_mass(Tc) = (5.55 +/- 0.12) * NA^2*epsilon*sigma^3 / W^2
b_mass = (0.855 +/- 0.018) * NA*sigma^3 / W.
```

It recommends physical critical data for stable species because the simple
Lennard–Jones approximation is not sufficiently accurate for all stable fluids.
The constructed radical values are pseudo-critical parameters, not measurements.
[Giovangigli et al., Section 3.1, Eqs.37–43](https://www.cmap.polytechnique.fr/~giovangi/688.pdf)

For the present molar-SI kernel, use `NA` in molecules/kmol, `sigma` in metres,
`epsilon` in J/molecule, and `W` in kg/kmol. Multiplying the last three
mass-specific expressions by `W`, `W^2`, and `W`, respectively, gives:

```text
Vc_molar = 3.29*NA*sigma^3                 [m3/kmol]
ac_molar = 5.55*NA^2*epsilon*sigma^3       [Pa m6/kmol2]
b_molar = 0.855*NA*sigma^3                [m3/kmol].
```

CHEMKIN well depth is normally supplied as `epsilon/kB` in K; Cantera's
`species.transport.well_depth` is already in J/molecule. Applying kB twice
would be a unit error. Its transport diameter is already in metres.

The existing kernel accepts Tc/Pc/omega and reconstructs
`ac=0.42747*(R*Tc)^2/Pc`, `b=0.08664*R*Tc/Pc`.
A b-preserving encoding is
`Pc=0.08664*R*Tc/b`. It implies an attraction prefactor 5.551485 instead
of the rounded source value 5.55, a +0.02676% difference.
Alternatively, combining the source Vc with the SRK `Zc=1/3` gives
`Pc=R*Tc/(3*Vc)` and factors 0.8551368 for b and 5.5523736 for ac.
These small roundoff differences are below the source estimates' stated
uncertainties; they must still be documented rather than hidden.

The quoted estimates determine `ac`, `b` and a temperature scale. They do not
specify an acentric factor for every unstable species. The current table uses
omega=0 for many radicals. Extending that convention to additional radicals is
an explicit model assumption, not an additional measurement supplied by Eq.39.
Changing the alpha rule at the same time would add a second model change.

## Current input coverage

The inventory reads the exact author YAML files used for the ideal flames,
the existing 53-species GRI table, and the separately sourced He row.
USC `CH2*` is explicitly identified by its author as singlet methylene and maps
to the existing `CH2(S)` identity.

| Inventory | USC first | HP fixed-100-atm |
|---|---:|---:|
| Species | 111 | 92 |
| Positive author sigma and epsilon | 111 | 92 |
| Existing critical rows with explicit aliases | 35 | 36 |
| Species without an existing row | 76 | 56 |
| Name-only candidates in Cantera critical database | 19 | 15 |

The last row is a search result, not an approved mapping, and overlaps the
existing rows. The existing table itself mixes physical critical inputs with
pseudo-critical estimates; reuse does not convert an estimate into measured
data. Molecular weights must follow the chosen mechanism's atomic weights.

For example, applying the current author's transport values to H, O, OH and
HO2 gives Tc values 190.82, 105.28, 105.28 and 141.3384 K, respectively.
The b-preserving pseudo-Pc values are 30.988312, 7.082448, 7.082448 and
4.782124 MPa. The inherited table uses 31.009, 7.087, 7.087 and 4.785 MPa.
Those small differences are consistent with different rounding/constants; they
do not justify a change to an already identified baseline.

Case 3's current EOS/caloric kernel uses Tc, Pc and omega; Vc is not active in
that kernel. Vc is still retained in the shared species interface and used by
other property models. An SRK-implied pseudo-volume must not be labelled as a
measured critical volume merely to fill that field.

## Names alone are unsafe

The USC source explicitly identifies several isomers. The pinned Cantera
property database uses different names for the same structures:

| USC name and author identity | Corresponding Cantera database record |
|---|---|
| `C4H6`: 1,3-butadiene | `C4H6-1` |
| `C4H612`: 1,2-butadiene | `C4H6` |
| `C4H6-2`: 2-butyne | `C4H6-3` |
| `CH3CHOCH2`: propylene oxide | `C3H6O` |
| `CH3COCH3`: acetone | `C3H6O-3` |
| `C6H5CH3`: toluene | `C7H8` |
| `C6H5OH`: phenol | `C6H6O` |

In particular, a direct match on `C4H6-2` would silently select 1-butyne.
These structural crosswalks establish identity candidates only. Their critical
values still need source and quality labels. Formula matching also cannot
distinguish a radical, an excited state or an isomer.
[USC author input, species comments](http://ignis.usc.edu/Mechanisms/USC-Mech%20II/USC_Mech_ver_II.txt),
[Cantera v3.2.0 critical database](https://github.com/Cantera/cantera/blob/v3.2.0/data/critical-properties.yaml)

The Cantera database identifies its compilation and general NIST/Yaws sources,
but not a separate experimental citation for every record. It is a reproducible
software dataset, not proof that Liang used those values. Stable compounds such
as ethanol, propylene oxide and aromatic oxygenates should use explicit
structure/CAS assignments before property lookup. Unresolved names remain
unresolved in the inventory.

## Defensible implementation scope

A complete *declared estimate* can be built, but it must not be presented as
the unpublished Liang table:

1. Preserve the existing identified major-species inputs for a continuity
   control; record separately which are measured/compiled and which are inferred.
2. Map additional stable compounds by structure or CAS to a pinned, cited
   critical-data record. Retain database provenance and uncertainty limits.
3. For identified unstable species, calculate ac and b from that mechanism's
   author LJ values, with the formula and units above. Record the pseudo-critical
   interpretation and an explicit alpha/omega policy.
4. Fail on unclassified species or unresolved stable identities. Do not silently
   assign zero EOS parameters, inherit a formula-isomer record, or call every
   missing species a radical.
5. Compare properties at frozen states, including existing-major parity,
   `Cp=(dH/dT)_(p,X)`, partial-enthalpy identities and thermodynamic stability,
   before a full-mechanism Case 3 flame is qualified for use.

An all-LJ, omega=0 table would be a separate isotropic-fluid diagnostic. The
source explicitly limits its accuracy for stable substances, so it does not
remove the stable-data qualification step or constitute a reproduction input.
None of the alternative inputs should be chosen by how closely its flame-speed
curve follows Liang.

## Evidence

`state/liang-hydrogen-20261020/mechanism-critical-audit/` contains:

- `inventory.py` and its no-write plan interface;
- `results/inventory.json`, with mechanism/table/database hashes, each
  species' author LJ values, inherited rows and unassigned candidate data;
- separate USC and HP CSV inventories.

No production critical table, solver change, remote job or commit was made.
The full ideal-mechanism identities and conversion checks remain in the
[Figure 8(b) audit](liang-figure8b-implementation-audit-20261021.md).
