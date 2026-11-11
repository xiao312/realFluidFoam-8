# Reproduce Sharma Figures 1–2 with executable flamelets

The goal is a usable physical flamelet/manifold generation method for later
realFluidFoam/OpenFOAM FGM integration. A curve fit or score improvement alone
does not establish this. Preserve the old Famou closure tasks and their failures.
They do not block this independent paper-level development task.

## Stage A: qualify the provided execution path

1. Verify every manifest file hash. Record the Python and dependency versions.
2. Reuse Cantera 3.2 if available. Prepare an isolated project environment.
3. Install requirements.txt, then build vendor/Spitfire with
   `python -m pip install --no-deps --no-build-isolation ./vendor/Spitfire`.
4. Use the provided source. The unrelated PyPI package named spitfire is not valid.
5. BLAS/LAPACK and a C++ compiler are required. Report actual missing dependencies.
6. Run `python qualify.py --mechanism inputs/zk-author-2019.yaml --out runs/qualification-A1`.
7. Retain the command, exit, stdout/stderr and qualification.json, including failures.

The source is Sandia Spitfire 735711dc with two declared patches: interior chi
indexing and stable cold Arrhenius evaluation. The setup.py adaptation writes
explicit source metadata without a live Git repository. It changes no equations.
Compare warm production rates with Cantera and execute the actual small cryogenic
flamelet. Imports or compilation alone do not qualify physical execution.

Do not install OpenFOAM or a Cantera C++ SDK. No SSH, SCNet, Slurm, credentials,
purchase or subscription changes. Work within the existing free sandbox/resources.
Repair justified environment failures and keep evidence. Do not replace the
mechanism, numerical controls or qualification result to make a failure disappear.

## Stage B: reproduce and score the physical seed

Run `python platform_evaluator.py candidate.py`. It creates a new directory under
runs/, executes physical flamelets, then evaluates the output with evaluate.py.
The existing physical driver uses three independent equilibrium initializations:
chi=10000/300000/2000000 s^-1, 129 Z points, 1 ms. On SCNet they completed in
about 25 seconds of physical integration. Cloud timing is not yet known.

The new seed never pools different trajectories. For Fig. 2 it takes the first
downward crossing after maximum progress on the chi=2e6 quenching path. It
interpolates in Z explicitly. Fig. 1 uses the actual final chi=10000 profile,
which is not assumed identical to the paper's c=1 line. This is a declared weak
baseline, not a correct manifold by definition. Retain every original trajectory.

Expected local baseline combined_score is 0.30379346868824214, with mean coverage
0.998760555589491. Small platform/compiler variation must be reported. A large
score discrepancy requires diagnosis, not modification of the evaluator.

## Stage C: improve physical generation and branch construction

Keep pressure 6 MPa, author Zhukov–Kong mechanism, species and reaction data, and
the paper's c=(YCO2+YCO)/(YCO2eq+YCOeq) definition fixed. Stream temperatures
85/288 K, unity Le and ideal-gas flamelets are explicit reconstruction assumptions.
The paper names Fluent for CFD but does not provide generator files or exact
flamelet settings. It gives a 100x100 manifold and the four Fig. 2 slices.

Investigate the dissipation family, initialization, resolved time sampling,
physical branch selection and table construction. Numerical solver changes are
allowed. Equation/transport changes require a derivation, physical controls and
an explicit model-variant label. Do not tune chemistry or EoS parameters to curves.
Do not invent c values for the unlabelled intermediate blue contours in Fig. 1.

The candidate may import Spitfire/Cantera and shared input files. Its runtime
must not read reference curves, reference CSVs, baseline predictions or metrics.
Do not return fitted T/Y curves or select per-point states by closeness to paper.
The paper references are for the evaluator and analysis, not the physical runtime.
The evaluator is a process-level scoring contract, not a security sandbox.

Use a common, reproducible generation rule. The same state must supply T and
all species. Record path multiplicity rather than averaging it without a model.
Preserve gaps and material out-of-domain queries. Do not smooth away jumps,
silently discard failed states, clip coordinates or force zero chemical sources.
Record existing Spitfire clipping and cold-Cp behavior separately.

The physical deliverable includes a portable 100x100 table with coordinate
definitions, species order, Y, T reference, rho, absolute enthalpy and signed
species/progress sources with units. Include parent trajectory identities and
branch-selection metadata. The standalone CFD thermo remains responsible for
T/rho inversion; a table-temperature overwrite is not an integration solution.

## Fixed scoring and progress records

Fig. 2 has eight curves, with 80% aggregate weight. Fig. 1 burnt temperature and
six species have 20%. Curves receive equal weights within each figure. Dimensional
RMSE, normalized RMSE and coverage are returned for every curve. Temperature scale
is 4000 K, Fig. 2 CO2 scale 0.35 and Fig. 1 species scale 1. Missing predictions
incur one plus the worst admissible squared normalized error at that point.
They cannot improve a score by disappearing. Gross format bounds are 0..6000 K
and -1e-8..1+1e-8 mass fraction; these are not scientific acceptance thresholds.
Trapezoidal x weights avoid rewarding densely sampled raster segments.

Score = exp(-10*(0.8*NRMSE_fig2+0.2*NRMSE_fig1)-2*(1-mean_coverage)).
This ranks curve agreement. validity=1 means the output can be evaluated, not
scientific approval. Keep evaluator/reference hashes fixed across every result.
Do not alter the score in a platform wrapper. Return combined_score unchanged.

For every attempted candidate, retain source hash, settings, execution status,
wall time, all 15 curve metrics, aggregate score and physical evidence. Run the
same evaluator on failed/partial results where data exists. Do not report only
the best result. Add energy/element/progress consistency and path-ambiguity
diagnostics. Preserve approximately two-pixel reference uncertainty.

After actual runtime and seed qualification, proceed with physical development.
Use the existing gifted resources; do not purchase/upgrade. A small 10-round CPU
deep-evolution run is authorized for this task once its real seed is accepted by
the platform. Evolve candidate.py; keep shared physics/dependencies and evaluator
frozen. Candidate code can implement new orchestration using Spitfire APIs.
If deep evolution cannot launch, report the actual platform response and continue
useful bounded physical development; ordinary edits are not called deep evolution.
Do not repeatedly ask for already-authorized setup or physical runs.

## Delivery and independent evaluation

Deliver runnable source, all candidate metrics, settings, raw trajectories, table,
matched raw numerical curves and reference/prediction plots. Record actual model,
provider, tools and evolution experiment/seed/generation IDs when available.
Reports must distinguish numerical execution, paper agreement and table validity.

For the best physical candidate, perform a modest grid/time refinement and
additional mixture-fraction queries without fitting those queries. The operator
will rerun the returned code on SCNet and independently inspect the evidence.
No result is automatically approved for OpenFOAM/G2 or public publication.
