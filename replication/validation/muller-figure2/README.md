# Muller Figure 2 comparisons

This module extracts the published vector curves and compares computed methane/oxygen profiles.
It does not solve a flame, submit jobs, or approve scientific results.

Inputs are the owner's Muller and Pfitzner (2015) PDF and explicitly labelled CSV profiles.
Outputs are reference JSON, comparison figures, and numerical error summaries outside Git.
The PDF is bound by SHA256. Path indices and axis transforms apply only to that exact PDF.
The PDF remains private. No credentials or machine paths are stored here.

The extraction depends on PyMuPDF. Plotting also uses NumPy and Matplotlib.
The flamelet driver is independent. Its CSV must contain `Z`, `T`, and `Y_<species>`.
A `rho_PRVTA` column can supply reconstructed real-fluid density.
Ideal-gas `rho` must not be plotted as the paper's PR-VTA density prediction.

Figure 2 uses 5.61 MPa, methane at 288 K, oxygen at 85 K, and near-zero scalar dissipation.
The paper does not specify the numerical near-zero value. Equilibrium is a labelled limiting reference.
Finite-strain solutions must retain their measured scalar dissipation and convergence evidence.
The reduced-mechanism curves are reference data; this module does not claim to implement that mechanism.

Example:

```sh
python extract.py --pdf /private/muller2015.pdf --output /results/reference.json
python compare.py --reference /results/reference.json --profile /results/profile.csv \
  --label 'HP equilibrium limit, GRI30' --output /results/fig2
```

Verification: run extraction on the bound PDF, then inspect the four paper panels and extracted curves.
Extraction checks endpoint temperatures, density and species, plus curve identities and units.
Comparison records errors against the full-mechanism curves and never writes a scientific pass.
No extrapolation is used when a computed profile does not cover the paper's mixture-fraction range.

`extract_extinction.py --pdf PAPER --output FILE` also prepares Figure 3's
temperature-versus-scalar-dissipation curves. Its logarithmic abscissa is
calibrated independently. The published branch endpoint is not a calculated
extinction bracket; establishing that requires both burning and extinguished
calculations, with their inlet temperatures and numerical settings identified.

`branch_compare.py --branch RUN --reference FIG3_JSON --output NEW_DIR` verifies
the branch receipt and retained NPZ hashes without writing. Add `--apply` to
render both the burning range and all retained peak temperatures, plus CSVs for
Figure 2. Failed residual/process verdicts remain in the result and figure
legend. It does not infer extinction convergence from a cold final state. The
initial supported run has a known upstream energy-index defect; this limitation
is recorded explicitly. A tampered receipt or profile fails before rendering.
