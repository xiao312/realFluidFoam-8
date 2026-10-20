# Liang Figure 8(b) mechanism controls

This module runs ideal methane/air free flames with explicitly identified author
mechanisms. It tests Figure 8(b)'s kinetic-model comparison separately from the
GRI Case 1-5 model ablations. It does not claim that a full author mechanism is
Liang's unpublished methane subset, or repair invalid rates by clipping.

## Interface and boundaries

`kinetics-flame MECHANISM PHI NEW_OUTPUT [GUESS_CSV|-] [PAIRS_TXT|-]` uses 100 atm, 298 K, CH4 and
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
Profile headers use CSV quoting, including species names containing commas.
The reader supports quoted fields and doubled quotes and rejects malformed
records. Historical USC profiles have unquoted comma-bearing species names;
they require an explicit mechanism-order audit before positional recovery.
The driver does not silently reinterpret such malformed historical files.

`fixed_pressure_hp.py plan|apply AUTHOR_YAML NEW_OUTPUT` reproduces the qualified
HP input used by these controls. It accepts only the recorded author-YAML hash.
Seven signed PLOG channels become their unchanged Arrhenius terms at the exact
100-atm node or nearest endpoint. It does not interpolate a rate or change a
coefficient. Analytical positivity certificates apply to each summed channel
over 298–3500 K. Independent CGS-to-SI rate checks cover 3204 temperatures;
five composition states also check complete forward rates of progress.
The generated mechanism must reproduce the previously qualified SHA256.
Plan checks inputs and describes conversion without writing. Apply requires
a new directory and writes mechanism, reaction mapping and qualification.
Dependencies are pinned Cantera 3.2.0, NumPy and ruamel.yaml. This offline
preparer has no scheduler, network or secret dependency. It does not solve
a flame, validate rates outside its interval, or identify Liang's subset.
Example: `python fixed_pressure_hp.py plan hp-2017-author.yaml new-input`.

`subset.py plan|apply INPUT_YAML NEW_OUTPUT --max-carbon 2` prepares a labelled
structural sensitivity input. It retains all species with at most two carbon
atoms, all reactions whose participating species are retained, and only retained
third-body efficiencies. It preserves C2 methane-recombination pathways.
This is not an author-supplied methane subset and is never selected by agreement
with the paper. The JSON record lists removed species/reactions and verifies
retained forward/reverse progress rates against the full mechanism with omitted
species set to zero. Cantera Python 3.2, NumPy and ruamel.yaml are its offline
dependencies. Source YAML scalars/units are retained; the native Cantera writer
fails for the signed HP representation, so the preparer checks the serialized
YAML through a fresh Cantera load instead.
The fixed-100-atm HP input remains qualified only at 100 atm and 298–3500 K.
No model rates, thermochemistry or transport coefficients are fitted or repaired.
Plan performs discovery and reports the selection without writing files.
Apply requires a new output directory and passes the frozen-state rate check
before writing the input and its provenance. This does not establish that the
removed pathways are dynamically negligible in a flame.

`prompt_off.py plan|apply FIXED_HP_YAML FIXED_HP_QUALIFICATION NEW_OUTPUT`
isolates the baseline-versus-prompt distinction in Zhao et al. (2017), Liang's
reference 15. It removes exactly the three negative HCO correction channels and
their three positive direct H+CO partners (author reactions 46/47, 49/50, 52/53),
retains parent reactions 45/48/51, and clears only their now-unpaired duplicate
flags. Other H+CO pathways remain. Input hash and author-to-specialized reaction
mapping must match the qualified 100-atm input. It uses the same offline Python
dependencies and verifies every retained forward/reverse rate before writing.
This is a source-supported prompt-off diagnostic, not an identified Liang
methane subset. It remains restricted to 100 atm and 298–3500 K.

Optional `PAIRS_TXT` supplies named binary diffusion polynomials, one whitespace
row `species_a species_b d0 d1 d2 d3` per author pair. Its explicit formula is
`D[m2/s] = 1e-4*(101325/p[Pa])*exp(sum(d_i*ln(T[K])^i))`.
Only binary mass diffusivity changes. Ordinary mixture reduction consumes the
corrected pairs; viscosity and conductivity retain their ordinary models.
The author USC/Wang documentation identifies this as the mixture-averaged
diffusion extension. Its A*/B*/C* corrections for multicomponent/Soret transport
are outside this module, as is complete modified TRANSPORT program equivalence.
An omitted table keeps the LJ baseline. Unknown or duplicate pairs fail;
there is no implicit transfer of USC's table to another mechanism.
The configuration records the count and the job records the table hash.

Outputs are refinement/speed/temperature CSVs, a named-species profile, a saved
steady solution, input/binary hashes and source revision. The fixed-100-atm HP
input must have its documented SHA256; its unchanged signed Arrhenius endpoint
representation is qualified only at that pressure and 298-3500 K. Other input
variants require equally explicit identity records.
Each new job also retains its checked executable hash, immutable build/SDK paths,
escaped command, numerical-guess hash and actual Slurm resource allocation.

Dependencies: the pinned Cantera 3.2 C++ SDK, GCC 11.2, Bash and Slurm. The
module has no OpenFOAM dependency or secret handling. The comparison gallery
consumes its outputs. All generated files, HOME, caches, logs and temporary
paths stay under the supplied project root. Downloaded mechanism files remain
outside public Git.

## Execution and verification

`submit.sh plan|apply ROOT RELEASE SDK MECHANISM build|flame BUILD PARTITION PHI [GUESS|-] [PAIRS|-]`
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
Builds with a supplied pair table run binary-formula, symmetry, mixture-reduction,
and unchanged-thermal-conductivity checks at ten prescribed states before
qualifying the executable.
Every build also checks CSV round trips for the actual comma-bearing USC names,
ordinary profile headers, embedded quotes, empty fields and malformed records.

`plot.py plan|apply PAPER MANIFEST REFERENCE_JSON NEW_OUTPUT [--gri-sweep JSON]`
overlays completed ideal mechanism controls on the original Figure 8(b) panel,
preserving its physical scale and caption. Each manifest row supplies `job`,
`mechanism`, `transport` and a collected `result` directory. Duplicate displayed
mechanism/transport/phi points fail; select a declared run rather than silently
averaging repeated pilots. Incomplete runs are retained in the evidence record
but not plotted. The optional GRI sweep is the earlier versioned Case 1-5 result
summary; only its screened ideal points are used and its hash is recorded.
The independent reference JSON supplies pixel calibration and reading bounds.
Outputs are PNG/PDF, a comparison CSV and input/result identities. This offline
renderer uses PyMuPDF and the standard library, with no solver, scheduler or
network dependency. It cannot establish the unprovided Liang methane subsets.
Verify the original axes, marker legends, reported selected jobs and missing
reference points before publishing. No curve is fitted to the paper.
The untouched original retains the inset legend. On the computed overlay only,
its independently inspected image rectangle is cleared before drawing our data:
otherwise the new USC/HP curves cross the legend text. This measured rectangle
contains no reference curves and is recorded in the evidence JSON.
