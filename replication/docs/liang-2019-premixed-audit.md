# Liang 2019: reference method and implications for replication

19 October 2026. Liang uses a modified PREMIX planar-flame calculation, not
Nguyen's central ignition and OH displacement-speed method. The paper also
identifies a real-fluid enthalpy issue that merits a separate equation audit.
This does not establish a defect in our solver or explain the present diagnostic
disagreement by itself. No numerical inputs or running jobs changed in this review.

## Source and scope

W. Liang, W. Li, C. K. Law, *Laminar flame propagation in supercritical
hydrogen/air and methane/air mixtures*, Proceedings of the Combustion Institute
37 (2019), 1733–1739. Published online 5 July 2018.
DOI: [10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070).
[Princeton publication record](https://collaborate.princeton.edu/en/publications/laminar-flame-propagation-in-supercritical-hydrogenair-and-methan/).

The owner supplied `1-s2.0-S1540748918302530-main.pdf`, seven pages.
SHA-256: `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe`.
The PDF remains outside Git. Extracted text and page renders are in operator
state `state/liang-2019/`. PDF pages 2, 3, 4 and 6 were inspected visually,
including Eq.(3), model cases, flux units, and methane Fig.8.

Cross-check: Nguyen 2022, Section 5.3, Eq.(40), Fig.12 and reference [52].
Code inspection uses integration b279879 and the unchanged named baseline solver.

## Two routes to the flame speed

Liang Section 2 (printed p.1734) identifies PREMIX/CHEMKIN as the planar-flame
solver. Section 3 describes adiabatic planar flames in a doubly infinite domain.
Section 3.1 (p.1736) explicitly identifies burning mass flux as the eigenvalue:

`f = rho_u * S_L`, hence `S_L = f / rho_u`.

This is mass flow per unit area in a flame-attached frame, not an OH production
integral and not the mass flux through a stationary boundary of our transient box.
In SI, f is kg/(m² s), rho_u is kg/m³, and S_L is m/s.
Figure 4 uses g/(cm² s) and g/cm³; its speed figures use cm/s.
Convert f from g/(cm² s) to kg/(m² s) by multiplying by 10.

The original [Sandia PREMIX report record](https://ntrl.ntis.gov/NTRL/dashboard/searchResults/titleDetail/DE86004485.xhtml)
describes a steady boundary-value problem, finite differences and Newton iteration,
with time integration to aid convergence. This establishes PREMIX's general method;
it does not supply Liang's modified executable or exact input settings.

Nguyen instead evolves two ignition-generated fronts and evaluates a local
density-weighted OH displacement speed after the ignition transient decays.
There is no OH threshold or ignition kernel recipe to extract from Liang's
reported flame-speed method. A steady real-fluid flame solver would be an
independent reference; it would not duplicate Nguyen's transient algorithm.

Our tracked speed uses local gas-relative contour motion and density weighting.
For a steady translating planar flame with consistent thermodynamics and transport,
that quantity should approach f/rho_u. This is a physical correspondence, not
evidence that our current 5.94–5.99 cm/s has reproduced Liang's result.

## Reference curves and model choices

Liang Fig.8(a), printed p.1738, uses CH4/air at 100 atm and GRI-Mech 3.0.
Its progressive model cases are defined on p.1735:

| Case | Added model relative to previous case |
|---|---|
| 1 | Ideal-gas reference |
| 2 | SRK equation of state |
| 3 | Nonideal enthalpy treatment in the energy equation |
| 4 | High-pressure thermal conductivity |
| 5 | High-pressure mass diffusion |

The conductivity model is Ely–Hanley; mass diffusion uses Takahashi corrections
and a mixture-averaged formulation. Nguyen uses Chung transport and explicitly
notes this difference in the discussion of Fig.12. Liang does not use Nguyen's code.

The full-real-fluid GRI30 curve, Case 5 in Fig.8(a), is the relevant Liang target
for the full-model comparison. Cases 3–5 lie close together. Near phi=1.10,
the curve is approximately 7.0–7.1 cm/s by visual reading. This is not a new
digitized numerical datum. Nguyen's own Fig.12 red point is approximately
6.8 cm/s; its black Liang reference lies near 7.0 cm/s. Keep these targets separate.

Figure 8(b) changes the kinetic mechanism: GRI30, USC 2.0 methane submodel,
HP methane submodel, and Hashemi's methane submechanism. Several alternatives
give much lower speeds, roughly 2–4 cm/s in the displayed range. The authors
attribute substantial differences to high-pressure kinetics. Changing our
mechanism to approach another curve would change the benchmark, not validate
the GRI30 replication. Their Fig.9 specifically discusses missing/changed
pressure-dependent reaction pathways, including CH3+OH=CH3OH in GRI30.

## Enthalpy formulation: a new audit priority

Liang Eq.(3) and its discussion on p.1734 emphasize that real-fluid mixture
enthalpy contains interactions between species. It is not generally the
mass-weighted sum of pure-species enthalpies at the same state. The familiar
ideal-mixture transformation from enthalpy to a temperature equation can then
omit composition-dependent terms. Liang uses a total-enthalpy formulation.
The hydrogen comparison includes Case 3*, explicitly distinguished from Case 3,
to show the consequence of the temperature-equation approximation.

Our deployed case selects `sensibleEnthalpy`. The baseline `EEqn.H` solves
`thermo.he()` with chemistry heat release, pressure work, kinetic energy, and
species-diffusion corrections. Its conduction conversion uses `kappa/Cp`
and individual `hei` fields. These terms deserve a direct equivalence check
against real-fluid mixture enthalpy and Fourier/species enthalpy fluxes.

However, the variable name is not a proof of error: a sensible-enthalpy equation
can be equivalent if the reference-energy, reaction and transport terms are
handled consistently. The library mixture code also calls `calculateRealGas`
and `updateEoS` after species mixing. It cannot be classified as a simple
ideal-mixture enthalpy sum from the initial weighted-addition lines alone.

The next audit should compare mixture derivatives with the deployed heat-flux
conversion and species enthalpy definitions. Measure the residual rather than
replacing the energy equation from terminology alone. A thermodynamic/model
mismatch and the instantaneous-versus-tracked Eq.(40) discrepancy remain
separate questions. Correcting one need not correct the other.

## Information still missing

The supplied seven-page paper does not give a reproducible modified-PREMIX deck,
finite domain endpoints, mesh/refinement tolerances, solver tolerances, convergence
criteria, or a species-by-species real-fluid parameter file. Minor-species critical
parameters use Lennard–Jones estimates; NOx EOS parameters are neglected for methane.
These choices need checking against our library data before claiming model identity.

I did not find an explicit numerical unburned temperature in this supplied Liang
article. Nguyen explicitly specifies 298 K. Do not treat 298 K as independently
verified from Liang, or infer an exact value from the phrase room temperature.
Soret/radiation settings and the full modified-PREMIX implementation are likewise
not specified sufficiently here to reproduce every numerical detail.

## Consequence for the current work

1. Retain the Nguyen transient case and its Eq.(40) checks as one replication path.
2. Use Liang's mass-flux definition to structure an independent steady-flame check,
   with real-fluid thermodynamics; an ideal-gas flame solver is not equivalent.
3. Audit energy/enthalpy and source evaluation alongside the next controlled
   time-step/ODE tests. Do not assume mesh refinement alone will resolve them.
4. Compare GRI30 with the matching full-real-fluid curve. Keep Nguyen's own
   approximately 6.8 cm/s result separate from Liang's approximately 7.0 cm/s.

This review adds evidence and priorities only. It does not establish convergence,
change a kinetic mechanism, or authorize a claim that either publication is wrong.
