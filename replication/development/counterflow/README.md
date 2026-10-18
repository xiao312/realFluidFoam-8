# Tutorial and paper counterflow variants

This draft makes the difference between the shipped 11,200-cell tutorial and
the paper meshes explicit. It prepares fresh two-stage cases; it does not change
the solver, chemistry tolerances or existing jobs. Dependencies: author-counterflow
and paper-campaign preparation, runtime density probe and OF8 mesh tools.
Dependent: future mesh/convergence comparisons. No secrets or external writes.

Inputs: condition `oxy-1|oxy-200|air-100`, variant `tutorial|paper`, new output
directory. Outputs: two-stage dictionaries, variant manifest and file hashes.
`plan` reports the mesh without writes; `apply` refuses existing output. Tutorial
means the existing author port (with declared high-pressure adaptations).
Paper means the published conditions plus a declared reconstruction of its mesh.

| Condition | R x L | Paper radial spacing | Near-flame axial spacing | Reconstructed cells |
| --- | --- | --- | --- | ---: |
| Oxyfuel 1 atm | 20 x 20 mm | 20 micrometres | 20 micrometres | 888,000 |
| Oxyfuel 200 atm | 5 x 5 mm | 5 micrometres | 5 micrometres | 816,000 |
| Air 100 atm | 20 x 20 mm | select 5 micrometres | 5 micrometres | 7,912,000 |

For air, the paper says 5-micrometre mesh in the flame zone without a directional
table. We select uniform 5-micrometre radial spacing as the conservative reading.
This supersedes the earlier draft assumption of 20 micrometres radially.
The original three-zone wedge geometry is retained. The central 40% of axial
length is uniform; outer blocks stretch away from it. The paper does not give
zone extents or stretching ratios: these are reconstructed and must be checked
against the actual flame location. For oxyfuel the outer endpoint spacings are
approximately 20–30 and 5–10 micrometres. Air stretches from about 5 to 100
micrometres outside the central zone. No claim of identical publication mesh.

Paper oxyfuel uses exact 21/79 molar O2/CO2 conversion, 300/1000 K streams,
strain=100/s and equal momentum using actual library densities. Tutorial uses
the original rounded Y(O2)=0.162 and fixed 1-atm velocities 0.467/0.533 m/s.
At the lateral paper outlet, p retains totalPressure while other primitive fields
use zeroGradient as described in section 5.2. Tutorial keeps its original mixed
inletOutlet/pressureInletOutletVelocity choices. Air retains the published-reference
adaptation (300 K streams, fuel 1 m/s, matched mass flux), which is documented
separately from the original 1-atm example. Source numerics/GRI30 remain unchanged.

Example: `python prepare.py plan oxy-200 paper OUTPUT` then `apply`.
Before CFD, run blockMesh/checkMesh and the library inlet probe plus
`validation/flames/finalize_inlets.py CASE` for each phase that has pilot.json.
Do not run large-grid GRI30 on a login node or apply tutorial resource limits
blindly. First qualify geometry and memory in Slurm, then map checked coarse
fields with documented interpolation and conservation checks.

Verification: all six plans, generated counts/spacing and preserved fvSchemes,
scheduled mesh checks, inlet strain/momentum/composition, field transfer and
centerline/radial sampling. Acceptance requires multiple resolutions, stable
profiles and comparison with the paper curves. The 100-atm chemistry failure
must be resolved in a separate numerical-control/solver draft before a large run.

`check_meshes.sh RELEASE JOB` runs inside the pinned container in a scheduled
allocation through validation stage `dev-counterflow-mesh`. It generates all
three paper variants, checks identical phase mesh dictionaries and requires
blockMesh/checkMesh success. It runs no chemistry and does not qualify flow.


## Corrected reacting runs

`refine.py plan|apply CONDITION JOB_DIR` prepares a new paper-resolution oxyfuel
case and copies only a pinned stable coarse checkpoint into a private donor.
It never modifies the source job. `run_refined.sh RELEASE JOB CONDITION` builds
our rename-only solver, qualifies the mesh, finalizes exact inlet composition
and momentum balance, and maps primitive fields with OF8 `mapFields`.
Only T, p, U and the 53 species are mapped; enthalpy, density and transport are
recomputed. Target boundary conditions remain those of the new paper case.
The mapping is a warm start, not a conservative restart or scientific result.
Hashes, field ranges and species-sum checks are recorded before time integration.

The first allocation is a bounded 10-microsecond qualification on 32 cores.
It measures memory, initialization and per-step cost on the actual fine mesh.
Controls: maxCo=0.2, maxDeltaT=1e-6 s, initial deltaT=1e-7 s. These are selected
numerical controls, not settings stated by the paper. Chemistry and PIMPLE
settings remain the original tutorial values. No steady-state claim follows.
Air is prepared separately but not launched at full resolution until its chemistry
failure is reproduced and resolved; the current coarse air state is not a valid
steady donor. Do not submit a long run before this qualification succeeds.

Verification: dry-run plans; checked source checkpoint hashes; identical GRI30
species lists; all generated species fields; preserved target boundary types;
mesh and normalized-field checks; isolated solver hash/ldd; timed Slurm run.
All generated state stays below JOB_DIR inside the project root. The runner
uses the existing environment, property probe and adaptive field inspector.
