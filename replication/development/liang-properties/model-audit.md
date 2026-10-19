# Liang Figures 1–2 and OpenFOAM model audit

2026-10-19. Read-only research; no solver changes or jobs were made by this audit.

Follow-up: the [Figure 2 coefficient and inflection audit](../../docs/liang-critical-audit-20261019.md)
tests the native critical construction independently and records the unresolved
incompatibility between the paper's paired curves and the specified mixing rule.

The fork already contains SRK thermodynamics, nonideal mixture enthalpy, and a
Takahashi diffusion correction. The missing work is chiefly independent model
selection, Ely–Hanley conductivity, and verification of the energy/diffusion
formulation. It would be incorrect to say that the OpenFOAM family lacks SRK.

## Sources and identity

- Liang, Li and Law, *Laminar flame propagation in supercritical hydrogen/air and
  methane/air mixtures*, Proceedings of the Combustion Institute 37 (2019),
  1733–1739, [DOI](https://doi.org/10.1016/j.proci.2018.06.070).
  User PDF: `C:/Users/xiaox/Desktop/1-s2.0-S1540748918302530-main.pdf`, SHA256
  `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe`.
  Read PDF pages 2–4 and 7, plus rendered page 3. Figures are on printed page 1735.
- Fork inspected at `728f122a5a604af55abd306bbe2a348da582d49c` in
  `state/worktrees/reacting-integration`. Paths below are relative to that tree.
- Cantera source reference only: v3.2.0, commit
  `4a8358eb80cfeb50474386b5f9ec0b3a83519889`, `state/cantera-v3.2.0`.
  No nonideal Cantera flame calculations are proposed or performed here.
- [Ely and Hanley (1983)](https://pubs.acs.org/doi/10.1021/i100009a016),
  *Prediction of transport properties. 2. Thermal conductivity of pure fluids
  and mixtures*, 22(1), 90–97: the paper's conductivity reference.
- [Giovangigli, Matuszewski and Dupoirieux (2011)](https://doi.org/10.1080/13647830.2010.527016),
  *Detailed modeling of planar transcritical H2–O2–N2 flames*: Liang reference 10
  for minor-species Lennard–Jones estimates. A primary full preprint was later
  located; see the addendum below.
- [NIST oxygen fluid page](https://webbook.nist.gov/cgi/fluid.cgi?Action=Page&ID=C7782447):
  current reference-data source. New database evaluations must be distinguished
  from digitized historical paper markers.

## Figures to reproduce

| Panel | Material/conditions | Axes and curves |
|---|---|---|
| Fig. 1(a) | Pure O2, 100 atm = 10,132,500 Pa | Density kg/m3 versus T/K; black model line and black triangular NIST reference markers. Display approximately 220–1000 K and 0–230 kg/m3. |
| Fig. 1(b) | Same pure O2 isobar | Thermal conductivity W/(m K) versus T/K; black model line and black triangular NIST markers. Display approximately 100–1000 K and 0.01–0.15 W/(m K). |
| Fig. 2 | Unburned H2/air and CH4/air across phi approximately 0.6–2.0 | Dual y axes: Tc 60–160 K in black and Pc 10–60 atm in red. Solid lines H2/air, dashed lines CH4/air. No experimental markers. |

The Fig. 1 caption identifies density and conductivity for oxygen at 100 atm.
The text assigns density to SRK and conductivity to Ely–Hanley. It acknowledges
discrepancy below room temperature. Do not change the conductivity model to
force agreement with the NIST markers, since the paper model itself differs.
The plot ranges above are visual estimates; extract PDF geometry for final layout.

For Fig. 2 the paper explicitly says it calculated the critical points as the
inflection point of the SRK P–v diagram. At fixed mixture composition this is a
cubic-EOS inflection/pseudocritical construction, not a proof of the full
multicomponent critical locus based on composition stability. Do not substitute
Kay's linear averages or Chung's transport pseudo-critical values.

Air 21/79 molar O2/N2 is the existing campaign convention; the supplied Liang
main text does not give an exact air-ratio input deck. Record that assumption.
Fig. 1 pure O2 and Fig. 2 fresh mixtures do not need chemistry integration.

## Existing implementation and gaps

1. `src/thermophysicalModels/specie/equationOfState/soaveRedlichKwong/` implements
   actual SRK, not RK or PR. `soaveRedlichKwongI.H` evaluates cubic Z, density,
   departure enthalpy H, departure Cp, and Cp–Cv. `rho=p/(Z R_specific T)`.
   Public accessors `bM()`, `coef1()`, `coef2()`, `coef3()` expose coefficients.
   Its attraction is `a(T)=coef1-coef2*sqrt(T)+coef3*T`.
2. `src/thermophysicalModels/reactionThermo/mixtures/SRKchungTakaMixture/`
   computes `b=sum Xi bi` and pairwise `a=sum Xi Xj sqrt(ai aj)` with zero binary
   interaction correction. It updates the mixed EOS before evaluating mixture
   properties; this is stronger than merely averaging pure-fluid enthalpies.
3. `src/thermophysicalModels/specie/thermo/rfJanaf/rfJanafThermoI.H` adds EOS H
   to NASA ideal absolute enthalpy and EOS Cp to NASA Cp. `Hs=Ha-Hf`.
   The existing nonideal mixture enthalpy is reusable.
4. Registered `forSRKchungKineticGases.H` and `forSRKchungTakaGases.H` hardwire
   rfJanaf with Chung transport and either kinetic or Fuller/Takahashi diffusion.
   These are not independent Case 2/3/4 switches. In particular, selecting SRK
   currently also selects nonideal enthalpy and Chung conductivity.
5. `chungTakaTransportI.H::Dimix` applies the Takahashi pressure correction to
   Fuller dilute binary coefficients, then returns `(1-Yi)/sum(Xj/Dij)` with
   cm2/s-to-m2/s conversion. Liang specifies Takahashi and mixture averaging but
   does not give a complete dilute binary diffusion input specification. If
   Cases 4 and 5 switch both dilute base and pressure correction, that is not an
   isolated Takahashi effect. Preserve a common dilute coefficient model.
6. No Ely–Hanley conductivity implementation was found in this source family.
   Cantera v3.2 `src/transport/HighPressureGasTransport.cpp`, lines 350–556,
   provides a readable implementation of Ely–Hanley 1983 conductivity, its
   shape factors and methane reference correlations. Its conductivity can be
   used as a source reference without importing Cantera flames or its bundled
   Lucas viscosity. Retain license attribution if code is adapted.
7. `replication/development/solver/EEqn.H` evolves sensible mixture enthalpy,
   but approximates heat conduction using `laplacian(kappa/Cp,he)` together with
   species-enthalpy/Y corrections. Liang specifically cautions against deriving
   temperature transport by treating nonideal mixture h as `sum Yi h_i`.
   Audit the complete identity and diffusion enthalpy definitions before calling
   this the paper's Case 3. A conservative enthalpy equation with explicit
   Fourier heat flux `-kappa grad(T)` avoids that particular gradient identity.
   Sensible versus absolute enthalpy as the stored variable alone does not prove
   inconsistency: formation-enthalpy transport/source terms must be transformed
   consistently. If absolute enthalpy is introduced, do not retain a duplicate
   formation-enthalpy Qdot source.

## Smallest defensible implementation sequence

1. Add a separate property-validation module using the existing OpenFOAM library
   build and pinned species data. Reuse the `rfPropertyProbe` runtime loading
   pattern for pure oxygen SRK density. Extend the sweep to the actual Fig. 1
   temperatures and explicitly record which temperatures are outside NASA7's
   stated 200 K lower bound. Do not silently relax `Tlow` or plot clipped 200 K
   values against lower requested temperatures. EOS-only density/critical probes
   can avoid temperature inversion and caloric bounds entirely.
2. Implement a small standalone, unit-explicit Ely–Hanley kernel, with a public
   input structure for species Tc/Pc/Vc/omega/W/Cp, composition, T, rho, and the
   volume choice used by conformal mapping. Attach it through an independent
   conductivity selector; do not silently change viscosity or diffusion.
   Qualify pure O2 against the Fig. 1 model line and fresh NIST values separately.
   Then qualify mixtures. Cantera's reference uses partial molar volumes; an
   OpenFOAM mixture port must deliberately supply consistent values, not reuse
   one mixture volume for every species without documenting the approximation.
3. Implement the fixed-composition SRK critical-point property probe described
   below, and report residuals of both pressure derivatives. This can directly
   consume the existing library's mixed coefficients. It does not require
   combustion solver modification.
4. Before staged flame runs, provide explicit EoS, caloric-departure,
   conductivity, and pressure-diffusion controls. Print each chosen model and
   the species-data hash at runtime. Defaults must preserve the qualified ideal
   and historical real-fluid families. Cases 1–5 must change only the intended
   model component. Test source-term and energy conservation separately.
5. Liang states it modified Ely–Hanley mixing/conformal mapping for rich H2/air
   but supplies no complete coefficients in the main paper. Fig. 1 pure oxygen
   does not require that modification; do not describe a later rich-hydrogen
   flame curve as an exact replication without resolving it.

## Fig. 2 reproducible analytic check and observed discrepancy

At fixed X, define `q=vc/b`. Solving `dP/dv=0` and `d2P/dv2=0` for SRK gives:

```
q = 1 + 2**(1/3) + 2**(2/3)
Omega_b = 0.086640349965
Omega_a = 0.427480233540
a(Tc)/(R*Tc*b) = Omega_a/Omega_b
Pc = Omega_b*R*Tc/b
```

For the library's geometric mixing on the positive attraction branch, write
`sqrt(a_mix)=A-C sqrt(T)`, where
`A=sum Xi sqrt(ac_i)(1+m_i)` and `C=sum Xi sqrt(ac_i)m_i/sqrt(Tci)`.
Then `Tc=[A/(C+sqrt((Omega_a/Omega_b) R b))]^2`. Alternatively solve the
temperature equation directly using the library's three coefficients.

Derivative checks at the resulting Tc, vc:

```
dPdv = -R*T/(v-b)**2 + a*(2*v+b)/(v**2*(v+b)**2)
d2Pdv2 = 2*R*T/(v-b)**3 - 2*a*(3*v*v+3*b*v+b*b)/(v**3*(v+b)**3)
```

An independent arithmetic check (not a compiled OpenFOAM result) used the actual
repo major-species data and its `m=0.48508+1.5517*omega-0.15613*omega**2`:

| Fuel | phi | Tc K | Pc atm |
|---|---:|---:|---:|
| H2 | 0.6 | 113.781658 | 33.310443 |
| H2 | 1.0 | 105.105475 | 31.680833 |
| H2 | 2.0 | 89.684986 | 28.465473 |
| CH4 | 0.6 | 134.627485 | 36.800323 |
| CH4 | 1.0 | 136.646100 | 37.147197 |
| CH4 | 2.0 | 141.111669 | 37.904458 |

These do not closely match the paper's Fig. 2, particularly pressure. Visual
readings at phi=1 are roughly H2 Tc=97 K/Pc=21 atm and CH4 Tc=138 K/Pc=41 atm;
these are not calibrated digitization results. Preserve this discrepancy and
test the compiled library output against the independent calculation first.
Do not tune species constants or relabel a different critical construction to
force agreement. The original authors' implementation/input data may be needed
to explain the mismatch.

The input file is
`replication/validation/flames/author-counterflow/original/GRI30/constant/thermo.inputData_GRI`:

| Species | Tc K | Pc MPa | Vc cm3/mol | omega |
|---|---:|---:|---:|---:|
| H2 | 33.18 | 1.3 | 64.935 | -0.216 |
| O2 | 154.58 | 5.043 | 73.529 | 0.025 |
| N2 | 126.19 | 3.398 | 89.445 | 0.039 |
| CH4 | 190.6 | 4.61 | 98.6 | 0.011 |

`rfSpecie.C` multiplies input Pc by 1e6. Vc requires explicit conversion in a
new SI kernel: cm3/mol to m3/kmol is a factor of 1e-3. For mole-basis quantities
with molecular weights in kg/kmol, R is about 8314 J/(kmol K).

## Remaining uncertainties

Liang's main PDF does not supply the complete SRK species database, exact Soave
alpha polynomial choice, modified rich-H2 conductivity prescription, full
PREMIX input deck or raw Fig. 1/2 data. It states that minor-species parameters
come from Lennard–Jones estimates and NOx a/b parameters are neglected; the
existing GRI data must be audited before claiming the same treatment. Exact
species exclusions and zero-a/b edge cases need explicit handling in a new
model. Source-model equivalence, property agreement, stable runtime execution,
and converged flame-speed agreement are separate qualification steps.

## Implementation access and NIST retrieval addendum

The exact local source authority is
`D:/xiaok/work/FlamePilot/projects/realfluidfoam/state/worktrees/reacting-integration`.
It is sparse on Windows, so inspect upstream source using, for example:

```powershell
git -C D:/xiaok/work/FlamePilot/projects/realfluidfoam/state/worktrees/reacting-integration show 728f122a5a604af55abd306bbe2a348da582d49c:src/thermophysicalModels/specie/equationOfState/soaveRedlichKwong/soaveRedlichKwongI.H
```

Build against the full case-sensitive Linux source release. The existing probe's
`replication/validation/properties/Make/options` supplies headers from
`$(LIB_rfFoam8_SRC)/thermophysicalModels/{specie,basic,reactionThermo}/lnInclude`
and links `reactionThermophysicalModels`, `fluidThermophysicalModels`, `specie`,
`finiteVolume`, and `meshTools` from the qualified environment/build. Preserve
its immutable source, library, container, and binary identities in the new probe.

The generic `psiReactionThermo` API exposes rho/Cp/kappa but not SRK a/b. A
typed EOS or concrete mixture interface is required for the critical probe.
`soaveRedlichKwong<rfSpecie>(const dictionary&)` is available for pure species;
the concrete `SRKchungTakaMixture<ThermoType>::cellMixture(celli)` returns the
fully updated mixture ThermoType with inherited public b/coef accessors. Do not
evaluate a stale mixture object before its composition update. On that object:

```cpp
const scalar b = mix.bM();
const scalar c1 = mix.coef1();
const scalar c2 = mix.coef2();
const scalar c3 = mix.coef3();
const scalar a = c1 - c2*sqrt(T) + c3*T;
const scalar da = -c2/(2*sqrt(T)) + c3;
const scalar d2a = c2/(4*T*sqrt(T));
```

The derivative names above are local probe variables, not existing library
methods. `updateEoS(b,c1,c2,c3)` is public if a separately verified mixture
coefficient assembly is used. That route must distinguish reimplemented mixing
from a call through the compiled library's mixture object.

For independent O2 NIST data, reuse `fetch_nist.py` with a new dedicated output
directory and these parameters (do not overwrite its historical CH4 snapshot):

```python
params = dict(Action='Data', Wide='on', ID='C7782447', Type='IsoBar',
              Digits='12', P='100', TLow='100', THigh='1000', TInc='5',
              RefState='DEF', TUnit='K', PUnit='atm', DUnit='kg/m3',
              HUnit='kJ/kg', WUnit='m/s', VisUnit='Pa*s', STUnit='N/m')
url = 'https://webbook.nist.gov/cgi/fluid.cgi?' + urllib.parse.urlencode(params)
```

Check returned units, pressure, temperature coverage, phase labels, and finite
density/conductivity; hash the raw response and retain query plus retrieval time.
Full 100–1000 K data support conductivity; use the paper's narrower displayed
temperature window for the density panel. New NIST values are reference-model
evaluations, not newly performed experiments. Keep digitized paper triangles as
a separate reference series with pixel calibration and uncertainty.

## Primary reference 10 follow-up

The [author's publication list](https://www.cmap.polytechnique.fr/~giovangi/biblio_giovangigli.html)
links the complete [CMAP preprint 688](https://www.cmap.polytechnique.fr/~giovangi/688.pdf).
PDF pages 10–12 give radical estimates:
`Tc=1.316 epsilon/kB`, `vc=3.29 NA sigma^3/M`,
`a(Tc)=5.55 NA^2 epsilon sigma^3/M^2`, `b=.855 NA sigma^3/M`.
These are mass-specific; multiplication by M or M² converts to molar b or a.
Reported prefactor uncertainties are ±.006, ±.07, ±.12 and ±.018 respectively.
The authors discuss truncated and smooth Soave-alpha alternatives and prefer
a tanh continuation above reduced temperature one. That is not the fork's
unbounded polynomial. The preprint's Eq.42 prints a quadratic acentric-factor
coefficient .151613; the fork uses .15613. Treat this as a source discrepancy
to verify, not a reason to change coefficients silently. The source supplies
the radical construction, but not Liang's full methane input database or
Fig.2 implementation. Liang's citation for radical parameters does not establish
that it adopted every alpha, chemistry, or transport choice from this reference.

## Ely–Hanley reference-density mapping: resolved from primary code

The reference-mass-density mapping must include the methane-to-mixture molecular
weight ratio. This is supported directly by Ely and Hanley's original TRAPP
Fortran, not just dimensional inference.

Primary source: [NBS Technical Note 1039, April 1981](https://nvlpubs.nist.gov/nistpubs/Legacy/TN/nbstechnicalnote1039.pdf),
*A computer program for the prediction of viscosity and thermal conductivity in
hydrocarbon mixtures*. [NIST publication record](https://www.nist.gov/publications/computer-program-prediction-viscosity-and-thermal-conductivity-hydrocarbon-mixtures),
[government mirror](https://www.govinfo.gov/content/pkg/GOVPUB-C13-dc6cad90c53569abc571b009039a551b/pdf/GOVPUB-C13-dc6cad90c53569abc571b009039a551b.pdf).
Retrieved and inspected in memory; no additional files were written. A normal
browser User-Agent was needed for the NIST PDF retrieval.

Evidence chain:

1. Appendix B, printed p.58 / PDF page 66, `FUNCTION TCOND(DX,TX)`, calculates
   the equivalent density with the exact line:

   ```fortran
   D0 = 0.001 * DX * HX * CMW0
   T0 = TX / FX
   ```

   This line was also checked visually in a rendered crop, so its multiplication
   by `CMW0` is not an OCR inference.
2. Printed p.44 / PDF page 52 calls `THERMC(DX,TK,X)` before converting density
   for output using `DX = DX * CMX * DM(IU)`. `DX` in the transport subroutines
   is molar density (mol/L), not mass density. `CMX=sum Xi CMW_i` is the actual
   mixture mean molecular weight, calculated in `ECSTX`, printed p.49/PDF57.
3. Printed p.66 / PDF74 defines `CMW0=16.043`, the methane molecular weight.
   The same block gives reference critical density `.1628` g/cm3 for transport.
4. Table 4, printed p.15 / PDF23, explicitly assigns the reference conductivity
   density units g/cm3 and gives the methane translational conductivity
   correlation used by `TCOND`.

Thus, with OpenFOAM/Cantera SI quantities and molar volume in m3/kmol:

```python
rho_reference_g_cm3 = 1e-3 * h * MW_reference / V_molar
# Equivalently, with rho_mix in kg/m3 and MW in kg/kmol:
rho_reference_g_cm3 = 1e-3 * rho_mix * h * MW_reference / MW_mix
```

Here `MW_mix=sum Xi MW_i` is the physical mean molecular weight. It is **not**
the effective transport molecular weight used in the conductivity scale factor
`sqrt(f*MW_reference/MW_effective) * h**(-2/3)`. Confusing these two quantities
would introduce a different error.

Cantera 3.2.0's `HighPressureGasTransport.cpp` line 442 uses
`rho_reference = density()*h_m*1e-3`, where `density()` is mass density and `h_m`
is assembled from molar critical volumes. That differs from the primary TRAPP
conversion by the factor `MW_reference/MW_mix`; it should not be copied into
the new port. For pure O2 this factor is about 0.50136, so the uncorrected mapped
density is almost twice the molar-consistent value. The effect on conductivity
is nonlinear through the dense-fluid correlation; it is not a simple factor-of-two
conductivity correction.

### Primary oxygen implementation path and remaining variant choices

The original TRAPP listing explicitly contains oxygen in Table A1 (printed p.34,
PDF42), with its pure-fluid data in `DATA XPRP56` (printed p.73, PDF81). Its
complete pure-fluid computation path is available: `DCST` supplies corresponding
states factors/density, `THERMC` combines internal and translational contributions,
and `TCOND` plus Table 4 evaluate the methane reference conductivity. These are
direct primary equations/code for an oxygen calculation, though TRAPP's own
corresponding-states EOS is not Liang's SRK density law. For our Liang target,
use the pinned SRK density and explicitly document the conformal-map convention.

Do not describe a port of Cantera's kernel as a literal reproduction of the
complete 1981 TRAPP routine. The latter additionally applies `CORT`, printed
p.59/PDF67:

```fortran
CORT = ((1.0 - T0 * AMIN1(0.0, PSI*DFXDT)) * ZC0 / ZCX) ** 1.5
TCOND = (LAM0 + LAM1 * D0 + LAMX) * FLAM * CORT
```

`PSI=1` in the listing. Its corresponding-state factors are obtained through an
iterative mapping, whereas Cantera evaluates shape factors using partial molar
volumes and omits this `CORT` factor. The primary 1983 article was found but its
full publisher PDF was not accessible in this audit. Therefore the mass-density
conversion is resolved; exact equivalence of all 1981/1983/Liang conductivity
variants remains unverified. Record the implemented variant and compare with
Liang's original Fig.1 model line independently of modern NIST reference values.
