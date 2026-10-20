# Liang Figure 8(b) mechanism controls

This module runs ideal methane/air free flames with explicitly identified author
mechanisms. It tests Figure 8(b)'s kinetic-model comparison separately from the
GRI Case 1-5 model ablations. It does not claim that a full author mechanism is
Liang's unpublished methane subset, or repair invalid rates by clipping.

## Interface and boundaries

`kinetics-flame MECHANISM PHI NEW_OUTPUT` uses 100 atm, 298 K, CH4 and
21/79 molar O2/N2, mixture-averaged mole-gradient diffusion, no Soret/radiation,
and a 1-cm domain. A numerical initial guess comes from that mechanism's own
ideal HP equilibrium. It is not a transient CFD restart. The current interface
supports ideal Case 1 only; nonideal Case 3 needs an explicit complete species
critical-parameter table and separate qualification before implementation.

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

`submit.sh plan|apply ROOT RELEASE SDK MECHANISM build|flame BUILD PARTITION PHI`
plans or submits one build or ideal flame. `BUILD` is `-` for compilation,
otherwise a passed immutable build.
One CPU and two hours bound each scheduler job. Plan is read-only.

Example:
`bash submit.sh plan ROOT RELEASE SDK MECHANISM flame BUILD kshcnormal 1.1`.

Verify Bash syntax, a clean Git diff, successful source/binary/input identity
checks, and at least two converged refinement levels. Compare ideal GRI with
the earlier independent result before treating mechanism differences as new
physics. A completed job is not paper acceptance. Retain ambiguous USC
duplicate-record choices as distinct inputs; the negative-rate Hashemi input
is blocked until a source-supported resolution exists.
