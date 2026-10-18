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
| Air 100 atm | 20 x 20 mm | not specified; select 20 micrometres | 5 micrometres | 1,978,000 |

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

