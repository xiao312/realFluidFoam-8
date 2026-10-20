# Liang Figure 8(b) mechanism controls

This module runs ideal methane/air free flames with explicitly identified author
mechanisms. It tests Figure 8(b)'s kinetic-model comparison separately from the
GRI Case 1-5 model ablations. It does not claim that a full author mechanism is
Liang's unpublished methane subset, or repair invalid rates by clipping.

## Interface and boundaries

`kinetics-flame MECHANISM PHI NEW_OUTPUT [GUESS_CSV|-]` uses 100 atm, 298 K, CH4 and
21/79 molar O2/N2, mixture-averaged mole-gradient diffusion, no Soret/radiation,
and a 1-cm domain. A numerical initial guess comes from that mechanism's own
ideal HP equilibrium. It is not a transient CFD restart. The current interface
supports ideal Case 1 only; nonideal Case 3 needs an explicit complete species
critical-parameter table and separate qualification before implementation.
An optional named-species profile supplies only a steady numerical guess.
The reader maps `Y_<species>` columns explicitly, sets absent species to zero,
normalizes each row and records the maximum discarded mass fraction. It preserves
the supplied domain length and grid; the inlet composition still comes from PHI
and the new mechanism. A supplied guess skips the otherwise used fixed-temperature
preparation solve. Both paths solve the full energy equation for reported results.
Inputs require increasing x, finite fields and at least ten points. No transient
CFD checkpoint is consumed.

Outputs are refinement/speed/temperature CSVs, a named-species profile, a saved
steady solution, input/binary hashes and source revision. The fixed-100-atm HP
input must have its documented SHA256; its unchanged signed Arrhenius endpoint
representation is qualified only at that pressure and 298-3500 K. Other input
variants require equally explicit identity records.

Dependencies: the pinned Cantera 3.2 C++ SDK, GCC 11.2, Bash and Slurm. The
module has no OpenFOAM dependency or secret handling. The comparison gallery
consumes its outputs. All generated files, HOME, caches, logs and temporary
paths stay under the supplied project root. Downloaded mechanism files remain
outside public Git.

## Execution and verification

`submit.sh plan|apply ROOT RELEASE SDK MECHANISM build|flame BUILD PARTITION PHI [GUESS|-]`
plans or submits one build or ideal flame. `BUILD` is `-` for compilation,
otherwise a passed immutable build.
One compute thread and two hours bound each scheduler job. Plan is read-only.
The launcher requests 16384 MiB and five allocated CPUs for flame jobs,
or 3072 MiB and one CPU for builds. SCNet requires memory per allocated CPU
to stay below its 3569 MiB limit; the additional CPUs secure memory allocation.
OpenMP and OpenBLAS remain fixed to one thread.
The 111-species USC pilots exceeded the site's implicit 3569 MiB allocation
while constructing the inherited fine-grid problem. Memory is an explicit
resource setting; it changes neither the mechanism nor the numerical criteria.
`job.sh` records the actual Slurm allocation before loading the mechanism.

Example:
`bash submit.sh plan ROOT RELEASE SDK MECHANISM flame BUILD kshcnormal 1.1`.

Verify Bash syntax, a clean Git diff, successful source/binary/input identity
checks, and at least two converged refinement levels. Compare ideal GRI with
the earlier independent result before treating mechanism differences as new
physics. A completed job is not paper acceptance. Retain ambiguous USC
duplicate-record choices as distinct inputs; the negative-rate Hashemi input
is blocked until a source-supported resolution exists.
