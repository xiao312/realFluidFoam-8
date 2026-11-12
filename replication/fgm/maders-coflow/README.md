# Maders 2017 reacting coflow preparation

Prepare physical flamelets and explicit case inputs for Maders Figures 4–6.
This module does not submit jobs, fit paper curves or establish CFD validation.

Inputs: the retained DeepFlame DRM19 YAML (21 species, 84 reactions), versioned
case contract and a new output directory. Outputs: actual steady flamelet profiles,
raw species/source arrays, residuals, table-coordinate diagnostics and provenance.
The flamelets use Spitfire mixture-fraction equations with prescribed Peters scalar
dissipation, ideal-gas chemistry, adiabatic unity-Le transport, variable Cp and
enthalpy flux. They are table building blocks, not radial coflow profiles.

Dependencies: pinned Spitfire/Griffon, Cantera 3.2, NumPy, SciPy in an allocated
Linux environment. The future developed OF8 solver consumes the exported data.
No network, credentials, scheduler or arbitrary code execution is exposed here.

Example: `python flamelets.py --config case.json --out NEW_DIR --plan`.
Remove `--plan` within FlamePilot-admitted Slurm compute. Every flamelet uses a
fresh equilibrium numerical guess. No evolved CFD state is imported.
Verification: exact mechanism/source hashes; chemical rate interface; finite raw
profiles; mass/element/enthalpy errors; measured RHS residual and grid sensitivity.
A converged flamelet is not a comparison with the two-dimensional paper target.

## Source audit

Maders PDF pp.2–5 defines 298 K atmospheric methane/air, diluted fuel 55/45,
weighted progress gamma=sum(Yi/MWi), i=CO2,H2O,H2; bilinear lookup; Smooke transport.
Verhoeven 2011 thesis PDF p.44 (printed37) establishes volume fractions, 12 mm
fuel diameter, 27.5 mm outer radius, 0.1 m height, parabolic fuel Umax=0.23 m/s,
uniform air0.23m/s, outer no-slip and zero-gradient outlet except pressure.
Maders incorrectly calls the 12/55mm dimensions radii and prints an inconsistent
parabolic formula. Use the thesis geometry and standard axial parabolic profile
U(r)=Umax*(1-(r/Rfuel)^2); record this reconstruction, not exact author case files.
The thesis uses300K; default298K follows Maders, with a300K sensitivity planned.
One atmosphere=101325Pa and dry air O2:N2=1:3.76 are declared reconstructions.
Source reference: https://pure.tue.nl/ws/portalfiles/portal/3577661/719415.pdf
Maders: https://www.abcm.org.br/proceedings/view/COB17/0722

Gamma units are kmol/kg when MW is kg/kmol. Its volumetric source is kmol/m3/s.
Our planned CFD coordinate C=MW_H2O*gamma is dimensionless; its volumetric source
is kg/m3/s. A weighted-reader extension is required; the existing unweighted sum
must not silently be used. Signed sources remain signed. The table chemistry and
Smooke transport must not be replaced by Chung/SRK for the atmospheric replication.

Famou task preparation is separate. Account credit exhaustion prevents new
execution on12November; no new assignment is claimed.

`mesh.mjs --out NEW_DIR --plan` describes the reconstructed axisymmetric40000-cell
wedge. Remove `--plan` to write a fresh mesh case. Node built-ins only; no solver
execution or credentials. Actual `blockMesh`/`checkMesh` run in FlamePilot Slurm.
The inlet lip is zero-thickness and the structured mesh differs from the author's
unavailable unstructured100000-cell mesh. These are explicit diagnostic choices.
`reader_states.py` exports nine actual DRM19 cold/half-composition/equilibrium nodes;
`reader_probe.C` checks the real OF8 reader against them. They are parity controls,
not a physical flamelet table and never the table for a production coflow run.

`lookup_baseline.py` consumes only declared training profiles and query coordinates.
It performs mapped weighted-C piecewise-linear interpolation with explicit coverage
refusal. `evaluate_lookup.py` reads separate fixed held-out physical references and
predictions. It reports T/species/signed-source errors, coverage, weighted-C and mass
consistency without declaring scientific acceptance. These tools are the portable
Famou task contract; no external task is launched by running them. NumPy only.
