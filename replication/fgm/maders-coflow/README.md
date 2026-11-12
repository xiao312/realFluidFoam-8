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

`export_table.py` builds a v3 table from five declared physical profiles, explicit
cold mixtures and HP-equilibrium limits. Chi5/10 remain held out. Sparse progress
gaps are linear reconstructions, not additional solved flamelets. It verifies
finite composition and weighted C, writes NASA7 metadata and fresh seed inputs.
It depends on the existing direct-flamelet metadata exporter and NumPy/Cantera.
`prepare_case.mjs` consumes exact table/metadata hashes and creates a new coflow
case only. It reuses the existing NASA exporter and solver schemes. No submission,
credentials or evolved CFD import occurs. Its dry-run is `--table DIR --plan`.
The first case uses an analytical cold fuel column plus a hot ring at timezero,
40000cells, upwind convection, Smooke transport and stock buoyancy force/energy.
It is a startup diagnostic; comparison with steady paper data needs a stable time
history and mesh/scheme checks. NASA coefficients are unchanged; bounds extend to
290K for slight flow-induced cooling near298K. This extrapolation is declared.

After actual blockMesh, `apply_inlet.mjs CASE --plan` computes each actual fuel
face centroid and parabolic velocity. `--apply` replaces only the fresh inlet
placeholder with fixed values, retaining mesh hashes and measured flow quadrature.
It refuses evolved cases or an unexpected patch. It reuses the existing G2 ASCII
mesh parser; no dynamic boundary compilation or model fitting occurs.

`initialize_Ha.C` reuses the existing guarded runtime-initialization pattern with
stock-compatible types. On the actual fresh mesh, it constructs the selected
Smooke thermo, computes Ha from its own h/Hf and prescribedT/Y, verifies actual
mu/kappa dispatch, and writes the required time-zero/thermo-type marker. It does
not read evolved fields or change p/T/Y. The remaining inversion audit remains
unchanged. Use before decomposition and after setFields, within the admitted job.

Warm OF8 build packets must include the standalone fgmDimixPolicy.H dependency
used by the retained steadyFlamelet module, even when its optional real-fluid
optimization is disabled. Add that exact source directory to CPATH; do not edit
or copy files into the stock read-only OpenFOAM installation. Runtime Ha
initialization is performed after setFields and before decomposition. Its marker
binds actual selected thermoType at timezero, leaving the solver guard enabled.

Maders case controls now select the retained conservative-density repair and
64epsilon-only transported-Z roundoff policy, with explicit mixture-fraction and
mass-correction accounting. Neither the material-error bound nor the energy or
lookup checks change. The first uncoupled default-off template is retained in
older commits; it is not the selected physical coflow setup.

The selected Strang-source diagnostic opts into sourceRoundoffProjection for
64-epsilon-only raw-C input excursions. It retains exact strict table lookup,
material-domain refusal and explicit per-stage mass accounting. The actual-reader
probe must pass before a fresh CFD run; previous failed time step remains retained.

Z and C now use 1e-14 absolute linear tolerance with zero relative tolerance;
other equation tolerances are unchanged. The former 1e-11 stop produced a joint
coordinate coverage failure near the pure-fuel endpoint. Tighter solves passed
that failure without extending the table. The 9d5fcf6 run uses an immutable
before/after-hashed fvSolution patch with the same settings. Future generation
writes those settings directly. See [12 November progress](PROGRESS-20261112.md).
