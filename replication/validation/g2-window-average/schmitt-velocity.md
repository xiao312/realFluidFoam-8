# Schmitt Figure 21 velocity contract

Source: Thomas Schmitt, *Large-Eddy Simulations of the Mascotte Test Cases
Operating at Supercritical Pressure*, Flow, Turbulence and Combustion 105,
159–189 (2020), https://doi.org/10.1007/s10494-019-00096-y.
The supplied PDF SHA256 is
`f138b430e2cac438acf139d9a7f56d38e53adb11513346c69922734c1c419879`.

Figure 21 on printed page 180 (PDF page 22) plots centerline mean axial
velocity against distance. Its axes are `u_x/u_0` and `x/d`. The adjacent panel
shows mean and RMS oxygen mass fraction. Page 181 defines d as the oxygen
injector diameter. The supplied text does not give an explicit numerical u_0
or state unambiguously that this symbol is the oxygen bulk velocity. The
near-inlet curve near unity is consistent with that interpretation, but is
not sufficient provenance to silently assign a reference value. Figure 9
explicitly uses a different notation, u_bulk, for inlet profile normalization.

Section 3.3 (printed page 171) states that all statistics use Reynolds
averaging. The authors start statistics after one convective time based on
oxygen injection velocity and flame length, then average for 50 ms (Table 2).
The G2 conditions in section 3.1 are 56 bar, O2 at 83 K and CH4 at 300 K.
These differ from the current 5.61 MPa, 85/288 K Müller-based diagnostic.
The present sample line is at radius 0.1 mm, not the exact centerline.

Until numerical normalization and reference digitization are independently
resolved, the default review shows our axial velocity in m/s beside the
unchanged original figure. A later normalized companion must bind the actual
executed inlet audit and measured mesh diameter, with the interpretation of
paper u0 labelled as an inference. The current direct-g2-input stream velocity
is explicitly an ideal-gas planning placeholder; it cannot substitute for that
audit. This module therefore records normalization as unavailable, rather than
silently using that value. No digitized paper error, statistical convergence,
or exact case match is asserted.

Sampling implementation: the official OpenFOAM-8
[csvSetWriter.C](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/fileFormats/sampledSetWriters/csv/csvSetWriter.C)
`writeHeader` loop appends numeric Cartesian component indices. Thus U_0 is
Ux, U_1 is Uy, and U_2 is Uz for this x-aligned geometry. The offline evaluator
already accepts these columns and exact coordinate joins. No solver code or
runtime binary change is needed to sample U. A representative writer-format
fixture tests data plumbing only; it is not a simulated velocity profile.
