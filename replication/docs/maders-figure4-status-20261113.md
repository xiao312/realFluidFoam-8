# Maders Figure 4: 13 November 2026 inspection

The fresh eight-rank run failed before reaching its requested endpoint. Its latest
saved profiles reproduce the temperature scale and upper-plane centre temperature,
but the radial profiles remain too narrow. This is useful coupled-solver evidence,
not a satisfactory steady Figure4 replication.

Job127801087 used compiled solver268c35851cdfb65c784f24cce76dcd88503eaac3,
runtime probe111a6699b5e9897c92b58723a171f344593448c5 and environment
f46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793.
The case started at time zero; no evolved fields were imported. It requested0.5s.
Slurm recorded FAILED,exit1:0,7937seconds with8CPUs. Reported TotalCPU0 is
not qualified CPU accounting and must not be interpreted as zero compute use.

## Literature comparison at145.033ms

Reference: digitized filled-square Detailed–Verhoeven markers in Maders2017 Fig.4.
These are numerical literature references, not new experimental measurements.
All36/23temperature and39/45CO reference points are covered at H10/H40mm.
Metrics use raw digitized coordinates; display interpolation does not add weight.

| Measurement | H10mm | H40mm |
| --- | ---: | ---: |
| Temperature maximum, computed |2015.96K|2038.56K|
| Temperature maximum, digitized reference |1999.16K|2018.82K|
| Temperature-peak radius, computed |6.625mm|6.183mm|
| Temperature-peak radius, digitized reference |7.624mm|9.695mm|
| Temperature RMS error |339.60K|696.86K|
| CO mass-fraction RMS error |0.010418|0.020404|
| Maximum temperature change since140ms |5.09K|39.55K|

The H40mm near-axis sample rose from352.54K at60ms to1463.80K at145ms,
close to the reference's roughly1450K central region. The hot-region width and
outer falloff remain substantially different. CO peak amplitudes are close,
but their radial positions and falloffs disagree.

Full-profile agreement did not improve monotonically. Temperature RMS errors at
60ms were181.05/454.04K. The30saved times show that transient agreement can be
accidental. Do not select an earlier frame because it happens to fit better.
The final5.033ms interval still changes the upper temperature profile by39.55K.
No steady convergence threshold was declared or passed.

## Numerical stop

The last completed step was0.148209270120561s. At0.148303519061584s, rank6
stopped in the second-half source-stage entry check after the progress transport solve.
The failure was `Material source progress excursion exceeds 64-epsilon policy`.
MPI abort and PMIX messages followed; this was not a wall-time timeout.

At the reported cell, Z=0.14312663723114, rho=0.15948475089795kg/m3,
C=0.17343764148411. The actual executed table gives an interpolated upper bound
0.17343752899662626. The excess is1.12487484e-7, approximately0.65ppm of that
bound, compared with the configured absolute allowance1.42108547e-14.
It is physically small but exceeds floating-point roundoff. Its effect must be
measured before changing the policy. The evidence points to transported Z/C and
table-domain consistency; it does not prove source-ODE arithmetic overflow.

Before failure, logged maximum temperature was about2092K, species-sum error
6.66e-16, cumulative lookup corrections0 and stored internal-enthalpy mutation0.
These diagnostics do not establish full conservation or scientific acceptance.

## Retained analysis and next action

The local operator directory is state/maders-coflow-20261112. It retains the raw
compressed postProcessing data, terminal log, executed table and all30sample times.
`comparison-r11-145/` holds the four-panel comparison and run failure metadata.
`history-r11-terminal/` holds numeric histories and time plots. The central local
Argos ladder now offers both views under Maders Figure4. All71targets/12papers
and original images/captions are retained. Public Pages were not updated.

Reusable analysis is in replication/validation/maders-coflow: `plot.py`,
`history.py`, and `import-preview.mjs`. Their READMEs give the command interfaces.
Inspect the generated figures and verify all asset hashes before publication.

Next, reproduce the small post-transport progress-domain excursion with fixed
inputs, then test a physically consistent treatment of the coupled coordinates.
Preserve the original failed verdict. A new CFD test must start at time zero.
Longer integration alone is insufficient to diagnose the profile-width discrepancy.
No rerun or Famou experiment was launched at this inspection; the previous run
window has expired. No independent review or human scientific acceptance is assigned.
