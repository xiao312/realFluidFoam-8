# Instantaneous OH thermal-excitation proxy

This module implements the postprocessing approximation in Mueller and Pfitzner
(2015), page 9, equation (18), with a representative wavelength of 308 nm. It
consumes instantaneous, co-located temperature, density and ground-state OH mass
fraction. It does not change a solver, reaction mechanism or case generator.
It does not predict calibrated optical intensity or assign scientific acceptance.

The concentration proxy is

```text
f(T) = exp[-h*c/(lambda*kB*T)]
cOH = 1000*rho*YOH/W_OH                  [mol/m3; W_OH in kg/kmol]
cOHstar_LTE_proxy = cOH*f(T)             [mol/m3]
YOHstar_LTE_proxy = YOH*f(T)             [dimensionless]
```

Both proxies are retained because the paper's equation uses concentration while
Figure 7 labels mass fractions. Excitation changes negligible molecular mass in
this approximation. Neither output is ground-state OH relabelled as OH*.
`W_OH` comes from the exact phase metadata; h, c and kB use exact SI definitions.
No fitted scale, wavelength adjustment or temperature cutoff is applied. A zero
from exponential floating-point underflow is counted, not replaced with a floor.

## Input contract and interface

The JSON manifest schema is `oh-lte-samples/v1` (see `example.json`). Paths resolve
relative to the manifest. `phaseMetadata` names the existing Cantera metadata with
`species[].name` and `molecularWeight_kg_kmol`. `frames` supplies strictly increasing
`time_s` and one or several CSV paths per frame. Every CSV has numeric `x,y,z` in
metres; together a frame must contain `T` [K], `rho` [kg/m3] and `OH` [mass fraction].
Split-field files must have identical coordinates and row order. Values must be
finite, T/rho positive and OH within [0,1]. Missing rho or averaged input fields
are errors; there is no ideal-gas density reconstruction. See
[sample-interface.md](sample-interface.md) for the separate producer request.

`sampling.kind` must be `instantaneous-cfd` or `physical-flamelet-snapshot` and
`sampling.instantaneous` must be true. These are producer declarations, recorded
without claiming independent authentication. `provenance` must identify the run
or derivation and source; all input bytes and module source receive SHA256 hashes.
The module never reads credentials, contacts a service or submits work.

With more than one frame, set `averaging` explicitly to
`{method: "trapezoidal-samples", start_s: FIRST_TIME, end_s: LAST_TIME}` or null.
The requested window must match the retained endpoints and every frame must use
the same point coordinates. The average integrates each already-transformed
instantaneous proxy with physical time weights. It is a sampled estimate, not an
exact exposure integration or evidence of statistical convergence. The input
time spacing and maximum gap are reported. It never evaluates equation (18) on
TMean/OHMean/rhoMean, invents missing frames, or applies Favre weighting.

## Output and execution

```sh
node replication/validation/oh-lte-proxy/run.mjs --manifest INPUT.json --out NEW_DIR
node replication/validation/oh-lte-proxy/run.mjs --manifest INPUT.json --out NEW_DIR --apply
node --test replication/validation/oh-lte-proxy/proxy.test.mjs
```

The first command validates and prints a read-only plan. `--apply` writes
`instant-0000.csv` etc., optional `time-mean.csv`, and `receipt.json` only in a new
directory. Inputs remain unchanged. Output columns retain coordinates, time,
instantaneous T/rho/OH, the Boltzmann factor and the two explicitly named proxies.
The receipt records units, assumptions, input/source/output hashes, sampling window,
underflow counts, and `scientificAcceptance: false`.

Dependencies: Node.js standard library. Dependents: future G2 optical morphology
review and image rendering; neither is a solver dependency. Focused checks cover
units, nonlinear averaging order and rejection of non-instantaneous/incomplete
inputs. They are software checks, not physical validation. No actual CFD proxy
result is implied by this implementation commit.

## What an optical comparison would still require

This is an LTE population approximation. Fiala and Sattelmayer's underlying
method assumes thermal excitation and, for radiation proportional to population,
optically thin gas. Its demonstrated excitation balance is not a universal cutoff
for all methane/oxygen states. This module does not model chemiluminescent production,
quenching kinetics, self-absorption, instrument band response or calibration.

Version 1 deliberately performs no line-of-sight (LOS) integration. The current
finite midplane does not establish complete radial support. A future axisymmetric
LOS operator must receive verified annular cell bounds from the axis to the outer
emitting radius, masks for solid/unsampled regions and the explicit symmetry
assumption. For a piecewise constant annular proxy, its chord weight at impact
parameter b is `2*(sqrt(max(ro^2-b^2,0))-sqrt(max(ri^2-b^2,0)))`. Missing annuli
must not silently become zero. A wedge assumption cannot reproduce instantaneous
three-dimensional LES fluctuations. Apply population transformation before LOS
and averaging, preserve unnormalised values, and document any display-only scale.

Mueller's Figure 7 compares a developed-flow average collected over 0.01 s, with
additional four-half-plane spatial averaging. Our preliminary axisymmetric wedge
or short-time average is not that sampling procedure. Ground-state Sharma Figure 9,
Abel-transformed Singla data and raw LOS images require distinct comparison labels.

Sources:

- Mueller and Pfitzner (2015), *Large-Eddy Simulation of Transcritical LOX/CH4 Jet
  Flames*, page 9, equation (18), Figure 7; locally inspected PDF SHA256
  `889bba9dc807b9197efcabbebba5a06f1dbf9d55c26582d19c88fbd10f15a8b9`.
- [Fiala and Sattelmayer (2013), equations (3)-(4)](https://www.eucass.eu/component/docindexer/?id=4175&task=download).
- [NIST exact SI defining constants](https://www.nist.gov/pml/special-publication-330/sp-330-section-2).
