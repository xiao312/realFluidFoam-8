# Ideal-gas OpenFOAM flame-speed assessment

At the 19 October 2026 14:04 snapshot, all eleven production runs remain active,
covering approximately 25–31 microseconds of the planned 200 microseconds.
No steady CFD flame speed is accepted. The cases retain source 128d13d, binary
build 124870644 and library build 124657926. No new numerical-sensitivity jobs
were submitted in this update, and no existing run was changed or stopped.

At phi=1.10 over 25.918–30.918 microseconds, the left OH=2e-5 contour gives
5.1839 cm/s from density-weighted front tracking. The timestep-averaged source
used in the OH solve gives a median 4.9454 cm/s. The corresponding steady
Cantera result is 7.4670 cm/s. These CFD values are developing measurements,
not a final disagreement with the steady reference. The source-based speed
varies from 4.5464 to 5.3744 cm/s within that window.

The owner removed instantaneous-source speeds from the comparison policy.
Front tracking is primary; the actual species-solve source is a cross-check.
End-step rows still provide position, gas velocity and density for kinematic
tracking. Their instantaneous reaction-rate estimate is not used in the new
history figures or convergence criteria. Previous source-stage disagreement
alone does not justify a new timestep campaign.

## Aligning the front definition with Cantera

Cantera FreeFlame solves a stationary, planar flame with unknown mass flux.
Its temperature anchor removes translation freedom; it does not prescribe
the flame speed. The reported speed is inlet velocity, or mass flux divided
by unburned density. The local source code at Cantera 3.2.0, commit
4a8358eb80cfeb50474386b5f9ec0b3a83519889, confirms this in
`Flow1D::evalContinuity`. The Python initializer normally places the fixed
temperature near one quarter of the initial equilibrium temperature rise,
possibly at a nearby existing node. Use the saved anchor, not that approximation.

For phi=1.10, the saved anchor is 780.8722452267356 K. Each operating condition
gets its own saved anchor. CFD can track the two corresponding temperature
contours and evaluate the signed propagation velocity relative to local gas,
multiplied by local density divided by fresh density. With the normal directed
into fresh gas, this is `rho_f/rho_u * (V_front - u_f) dot n`.
For a steady planar travelling wave this equals the burning velocity referred
to unburned gas. During relaxation it is a density-weighted displacement speed.

Also compare front velocity directly relative to fresh gas and check constant
mass flux in the translating frame. Marker agreement alone does not establish
stationarity. Fixed reference temperatures at 20%, 50% and 80% of the Cantera
temperature rise provide a marker-sensitivity check; they must not follow the
instantaneous CFD maximum temperature. Temperature-based CFD histories have
not yet been extracted in this checkpoint; the displayed histories are OH-based.

The `anchors.py` exporter verifies the mass-flux identity at every saved
Cantera anchor. The source/method references are the official
[inlet boundary formulation](https://www.cantera.org/3.2/reference/onedim/governing-equations.html#inlet-boundary)
and [free-flame residual](https://www.cantera.org/3.2/reference/onedim/discretization.html#free-flames).
The introductory sentence in the discretization page reverses free-flame and
burner-stabilized mass-flux descriptions; use its free-flame equation and the
implementation, which agree with the inlet-boundary documentation.

The new local figure is `output/ideal-openfoam-20261019T1404-v2/ideal-openfoam-histories.png`.
Its JSON assessment retains snapshot and case identities, source CSV hashes,
window bounds, both fronts, secondary-marker availability and numerical values.
The 11-case paper comparison remains Cantera-only until CFD values qualify.
