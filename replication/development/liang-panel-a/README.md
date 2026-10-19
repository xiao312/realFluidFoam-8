# Liang Figure 8(a): staged planar-flame comparison

This module owns the ideal-gas operating-point sweep and paper-scale Figure
8(a) comparison. The owner's later 19 October instruction authorizes Cases 2–5.
Their implementation belongs to `../cantera-liang`; existing plots still contain
only calculated Case 1 results until qualified new data replace them.

Inputs: the supplied Liang PDF, existing ideal-gas Cantera 3.2 profiles, pinned
author GRI30 inputs. Outputs: independent
flame solutions, provenance records, reference digitization and comparison plots.
Configuration: 100 atm, Tu=298 K, phi=0.92–1.44 in increments of 0.02; retain
existing 0.05-spaced points. Liang's numeric Tu is not explicit in the main PDF.

The paper's five cases are ideal gas; SRK density; nonideal enthalpy; Ely–Hanley
conductivity; and Takahashi mixture-averaged diffusion, added cumulatively.
Only the first case is calculated here. The other curves are preserved in the
original panel and identified as paper results. No real-gas Cantera extension
is part of this module.

Dependencies: `ideal-baseline` mechanism adapter and solved profiles, Cantera
3.2.0, numpy, matplotlib and PyMuPDF. Dependents: the comparison PDF and Lark
project record. Cantera is independent of the active OpenFOAM jobs. Source PDFs,
raw profiles, caches and outputs stay in the project workspace, outside Git.
No credentials are accepted by module code.

Minimal example:

```
python replication/development/liang-panel-a/ideal_sweep.py plan EXISTING_PROFILES NEW_OUTPUT
python replication/development/liang-panel-a/ideal_sweep.py apply EXISTING_PROFILES NEW_OUTPUT
python replication/development/liang-panel-a/plot.py plan PAPER.pdf RESULTS.json NEW_FIGURE_DIR
python replication/development/liang-panel-a/plot.py apply PAPER.pdf RESULTS.json NEW_FIGURE_DIR
```

Plan is read-only; apply refuses existing output. Each new condition starts
from the nearest previously converged profile and updates the inlet composition.
Two fine grid levels measure the speed change. Completed conditions are saved
incrementally; a failed solve raises its exception and stops the sweep. The
source profile directory must be beside `cantera/author-gri30.yaml`, as produced
by `ideal-baseline`. Do not interpolate missing computations as solved points.

The plotter copies the original PDF panel and caption at 1:1 physical scale.
It maps only solved Cantera points onto calibrated paper axes, with a green
line and open circles. Connecting segments are visual guides. Paper typography,
line widths and markers are preserved. The output includes a side-by-side PDF
and PNG, a standalone overlay PNG, and a data/provenance JSON manifest. The
source PDF SHA must match the owner-supplied copy. The original paper is local
input and is never committed to the public repository.

Verification: compile Python sources without writing bytecode, check input and
result hashes, review each condition's pressure/composition/grid histories, and
visually inspect exported PNG and PDF pages. These checks establish what ran;
they do not establish model identity where source data are missing.
