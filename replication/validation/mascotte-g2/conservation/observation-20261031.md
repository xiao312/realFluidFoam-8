# First measured conservation audit

This is diagnostic evidence from the unfinished cold SRK transport run in job
126417539, not acceptance of a G2 solution. Four completed steps cover only
0 to 6.42437299961471 ns. A subsequent 8.90211770535 ns step is unfinished and
excluded from completed-state integrals; its raw records remain in the report.

The solver source is `d1b753347794fe419c7231469597e45c6ed055c0` and executable
SHA256 is `460a3950e61164a851543f8181778dbb6434161f0e8c85b405f4b8ded5b44551`.
The exact log SHA256 is
`7f28d69dc77fbf539caffa231606f2aef204267a265ff83bb0fc3559ecc38cc0`.
The input manifest SHA256 is
`f14b0d2819ba9f2174892b132e5a37bb5291ddc9aef148d641665f3b862d3946`;
it also freezes the executed dictionaries, source files and three open-boundary
mass-flux histories. Operator state retains the manifest, log, source receipt,
JSON and step CSV under `state/forge-direct-20261030/results/g2-conservation-r8`.

| Measured quantity | Value |
| --- | ---: |
| Cumulative final-state energy defect | −1.1664112e−6 J |
| Cumulative assembled-term defect | −1.2283056e−14 J |
| Cumulative logged equation residual × dt | −8.4585423e−15 J |
| Enthalpy coupling contribution | +1.1594420e−9 J |
| Pressure coupling contribution | −1.1675762e−6 J |
| Cumulative Euler mass defect | −2.4351544e−18 kg |
| Largest single-step mass defect / initial step mass | 6.0803e−16 |

The measured energy difference is dominated by the change in pressure between
energy assembly and the final PIMPLE state, rather than by the assembled energy
equation residual. This is an accounting decomposition, not proof that the
pressure algorithm is wrong. The final-step defect is 2.3828% of that step's
transported energy and 4.6144e−10 of the sensible-energy inventory; cumulative
defect / cumulative transported energy is −1.8783%. The tiny elapsed time makes
inventory normalization alone uninformative for a future longer run. No new
threshold or acceptance was introduced.

Boundary mass uses current-step phi multiplied by the actual step duration.
Printed timeNames have fewer digits than energyState times, so samples are
bound through the intervening Time marker, without interpolation. Declared
wall/symmetry/wedge zero-flux patches were not independently sampled. The kinetic
boundary-power reconstruction also includes final-versus-energy-stage kinetic
differences; it remains an estimate. These qualifications are explicit in JSON.

The next useful comparison is the same accounting over longer fresh runs and
the source-on split formulation, retaining exact source, time histories and
boundary fluxes. This module does not alter either solver or case settings.
