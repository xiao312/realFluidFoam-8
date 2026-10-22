# Pure-oxygen contact advection at 6 MPa (`schmitt2020-fig-5`)

Status: **prototype, not a result.** The equation-of-state and conservation layers work; the
advection scheme does not, and the reason is measured rather than guessed.

## What the registered target asks for

`schmitt2020-fig-5` states: p about 6 MPa, a density interface from 1000 to 100 kg/m3 with an
error-function profile, a uniform velocity of 10 m/s, dx = 0.01 m, refinement factors 2, 4, 6 and
t = 20 ms. Its four panels are density, temperature, pressure and velocity along the domain. The
density and temperature panels are the same statement in two variables - a dense cold state and a
light warm one in pressure equilibrium - and the scientific content is in the pressure and
velocity panels, where an inconsistent discretisation produces spurious oscillations across the
interface while a consistent one leaves both flat.

The reference image is `assets/schmitt2020-fig-5-paper.png`; the conditions above are the whole
of the text available here, so the shape of the error-function profile (half-width 0.02 m) and the
mapping of "n_x = 2, 4, 6" onto grid refinement are **inferred**, and are declared as such.

## What works

`schmitt_advection.py` builds the initial condition in the variables the target gives: p = 6 MPa
and u = 10 m/s everywhere, with the density following the error function. Temperature is **not**
imposed; it is the temperature at which SRK oxygen has that density at 6 MPa, which lands on
117.11 K at 1000 kg/m3 and 248.90 K at 100 kg/m3 - the two ends of the paper's temperature panel.
That agreement is a property of the equation of state, not of a fit.

Thermodynamics are Soave-Redlich-Kwong for pure oxygen with the Chung et al. (1988) dense-gas
viscosity and thermal conductivity, taken from `../cavalieri-properties/srk_chung.py` so the
equation of state is covered by that module's tests instead of a second copy. Two inversions are
needed and both are tested: density to temperature at fixed pressure, and internal energy to
temperature at fixed density. The second has to be bracketed above the temperature at which SRK's
liquid-branch departure enthalpy collapses, where the internal energy is not monotone; that
minimum is found once per density and cached.

The finite-volume update is conservative to roundoff: the change in the domain totals equals the
boundary flux integrals to about 1e-16 relative, reported in every run as a certificate rather
than as a tolerance.

## What does not work, and why

The convective flux is Rusanov (local Lax-Friedrichs) with optional MUSCL/minmod reconstruction.
At both orders the run is unusable: the retained coarse run `runs/order1-dx0.02/` reaches 3.1 to
19.9 MPa of pressure, -54.9 to +23.7 m/s of velocity, needs 46 048 clamped cell-steps and never
produces an interface crossing at all.

The cause is a property of the conserved formulation, not a coding slip. SRK oxygen has a large
negative internal-energy offset that differs by about 240 kJ/kg between the two ends of the
interface, so the *conserved* energy differs enormously across the interface even though the
pressure is uniform. A Lax-Friedrichs dissipation term proportional to that jump and to the
acoustic speed is then about **31 times** the physical advective energy flux across a one-cell
step; `test_schmitt_advection.test_rusanov_dissipation_dominates_at_a_one_cell_interface` pins
that number. The scheme is being asked to advect a 240 kJ/kg internal-energy offset with a
dissipation that is thirty times the transport term.

The fix is a flux whose dissipation is restricted to the star region - HLLC with the SRK sound
speed - or a scheme formulated in primitive variables. Neither is implemented; nothing here is
tuned toward the reference panels.

## Reading the retained run

`runs/order1-dx0.02/run-dx-0.02.json` is kept as the negative control: it shows what the
conservation certificate looks like when the states are wrong (residuals at 1e-16 while the
pressure reaches 20 MPa), which is exactly why a conservative update is not by itself evidence of
a correct solution.

Run it with `python3 schmitt_advection.py --out DIR --dx 0.01 0.005 --order 2`. At dx = 0.02 the
order-1 run took 2141 steps and about 160 s, so a two-resolution order-2 sweep is a ~15 minute
allocation once the scheme is admissible.
