# Scientific stages

Environment qualification precedes simulation. The current authorization covers
project setup and the environment needed to compile. No production flame campaign
is launched by the environment scripts.

| Stage | Paper target | Required comparison |
| --- | --- | --- |
| Properties | 2022 section 5.1 | Methane density, heat capacity, viscosity, conductivity against NIST; supplementary species/models when obtained |
| Counterflow | 2022 section 5.2 | CH4/O2-CO2 at 1 and 200 atm; CH4/air at 100 atm; temperature, species, density and transport profiles |
| Premixed | 2022 section 5.3 | CH4/air at 100 atm, 298 K; flame speed across equivalence ratio |

Before each stage, freeze the reference dataset, state grid, EOS, transport model,
kinetics, mesh, time settings, sampling method, and numerical tolerances.
Record differences from the paper instead of silently adjusting inputs to match curves.
The full premixed case and supplementary reference data remain gaps.

Later stages are the 2025 nitrogen Cases 4 and 3, then coaxial N2/H2 D4.
Both nitrogen cases use 3.98 MPa in the journal. These are nonreacting LES cases.

References: [2022 paper](https://doi.org/10.1016/j.cpc.2021.108264),
[2025 paper](https://doi.org/10.1016/j.cpc.2025.109600).
