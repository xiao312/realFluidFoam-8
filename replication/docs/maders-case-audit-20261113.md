# Maders Figure 4 case audit — 13 November 2026

The completed case is a diagnostic reconstruction, not an exact author-case
replication. Re-reading Maders and Verhoeven identifies material differences in
outer velocity boundary, spatial resolution/scheme, initialization and manifold
construction. No single cause of the narrower, inward-shifted flame is established.
No new computation was launched for this audit.

## Evidence and identities

- Maders 2017, PDF pp.2–5, especially Fig.1, Sections2.2/3 and Fig.4.
  https://www.abcm.org.br/proceedings/view/COB17/0722
- Verhoeven 2011, printed pp.37–38,43,45–49 (PDF44–45,50,52–56).
  https://pure.tue.nl/ws/portalfiles/portal/3577661/719415.pdf
- Actual case: Slurm127882841, source a4058db5d4de4d799e79eea7fb6d7f82433c5c73,
  cases/maders-cfd-r12 under the registered SCNet trial. Read actual inlet receipt,
  case contract, time-zero U/Z/T/p and model/scheme dictionaries on13November.
- Small retained reads: state/maders-coflow-20261112/boundary-audit-runtime.txt
  and boundary-audit-U.txt. Original PDF page2 was rendered and visually checked;
  its schematic contains information absent from the prose/text extraction.

## Boundary, model and initialization comparison

| Item | Literature | Executed case | Assessment |
| --- | --- | --- | --- |
| Fuel | 55/45 methane/nitrogen by volume in thesis | Mole fractions .55/.45; methane mass fraction .41174384 | Match in composition basis |
| Fuel velocity | Parabolic, maximum approximately .23m/s | Actual face values maximum .22997166, area mean .11522412m/s | Match to thesis; .23 is not the mean |
| Air velocity | Uniform .23m/s | Fixed uniform .23m/s | Match |
| Geometry | Thesis fuel diameter12mm, outer radius27.5mm, height100mm | Same dimensions, axisymmetric wedge | Reconstructed match; zero-thickness lip and structured mesh |
| Pressure | Atmospheric; Maders schematic101325Pa outlet | Fixed101325Pa outlet; inlet/wall pressure zero gradient | Nominal match; compressible thermodynamics differs from pressure-independent-density formulation |
| Inlet T | Maders298K; thesis300K | Both298K | Matches Maders;2K below detailed thesis reference |
| Outer velocity | Maders Fig.1 free slip; thesis no slip | noSlip | Matches thesis, differs from Maders schematic |
| Outlet velocity | Zero normal gradient | pressureInletOutletVelocity | Same outward-flow behavior; different if backflow occurs, not established by net positive flux alone |
| Scalar boundaries | Z=1/0, progress=0 at fuel/air; zero gradient at outer/outlet | Same Z/C; zero-gradient T/species at outer/outlet | Nominal match |
| Buoyancy/transport | Buoyancy, unity-Le FGM, Smooke conductivity/viscosity | Enabled; Smooke adapter and stock Fourier diffusion selected | Intended match; requires operator-level parity/sensitivity, not only matching dictionary names |
| Progress coordinate | Sum(Yi/MWi), CO2/H2O/H2 | Same sum multiplied by MW_H2O, including source | Equivalent constant scaling; not a different combustion variable |
| Initialization | Cold-flow solution, then ignite near exit at source-peak progress | Fresh analytic cold fuel column plus4mm high hot annulus at r5–7mm, approximately1843K | Does not match sequence; all our CFD starts at timezero |
| Numerical grid | Approximately100000 unstructured cells; thesis near-front spacing30–60micrometres | 40000 structured cells; axial400micrometres, radial100 inside fuel/215 outside | Material resolution difference; no grid-independence qualification |
| Spatial convection | Maders second order | First-order upwind for U/Z/C/Ha | Material numerical difference |
| FGM thermodynamics | Paper retrieves properties and T from manifold | Species/source lookup plus transported absolute enthalpy and runtime thermo inversion | Different coupling; need quantify deviation from adiabatic inlet-mixed enthalpy |
| Manifold | Counterflow strain family near equilibrium to extinction; thesis adds transient quenching profiles,201x201 table | Prescribed-Peters-chi Spitfire family;3 burning training profiles plus2 cold, explicit cold/HP-equilibrium bounds,129x129 mapped table | Substantial reconstruction; transient/extinction gap is interpolated, not physically solved |

Maders' prose labels12/55mm as radii and its printed parabolic relation is
inconsistent with its stated maximum/axis. Thesis dimensions and velocity are the
basis of our reconstruction. Doubling fuel flow to make .23m/s the mean is not
supported by the thesis. The air in Fig.1 is labelled23%O2/77%N2; our mass fractions
.233/.767 are consistent to the precision of those labels, not a21%-versus23%
composition error.

## What the current profiles imply

At0.97002670227s, the computed temperature peak lies at6.625mm (H10) and5.962mm
(H40); the digitized detailed-reference maxima lie near7.624 and9.695mm.
Our stoichiometric-Z contour lies near6.935/6.352mm. Temperature peaks have
Z=.1417/.1355, close to but richer than Zst=.124236. This locates the discrepancy
in the coupled mixing/flow/reaction solution; it does not isolate chemistry from
transport. Similar peak temperature does not establish the correct flame shape.

Source interpolation held-out temperature RMS14.23K does not qualify source
accuracy throughout the gap between extinguished and burning branches. Source
RMS3.63kg/m3/s and maximum error17.06 against global peak39.31 also leave room
for errors affecting flame stabilization. No evidence yet assigns the observed
radial displacement to this error alone.

Time-zero ignition can select a different branch or stabilization position. Since
measurement-plane profiles have now settled, startup cannot simply be used to
explain away the final mismatch. It needs a controlled initialization sensitivity.
The2K inlet-temperature difference is a lower-priority explanation for errors of
hundreds of kelvin caused mainly by radial displacement.

## Next discriminating checks

1. Keep the current run as baseline. Use separately identified cases for the
   Maders free-slip boundary and a bounded second-order convection scheme; then
   refine around the flame. Do not combine all changes and lose attribution.
2. Export axial/radial Z, C, velocity and enthalpy diagnostics. Compare existing
   thesis Z/progress plots as well as temperature/CO to distinguish a misplaced
   mixture field from an incorrect response at the same coordinates. Measure
   enthalpy deviation from Z*h_fuel+(1-Z)*h_air and source/lookup corrections.
3. Fill the missing flamelet branch with physical near-extinction/transient states,
   qualify held-out source behavior, and compare to a resolved physical-counterflow
   formulation rather than assuming prescribed Peters chi reproduces it exactly.
4. Test the paper's cold-flow-then-ignition sequence within a fresh timezero case
   that evolves through both stages. Do not import or relabel an evolved CFD field.

These are proposed diagnostics, not completed sensitivities or scientific approval.
