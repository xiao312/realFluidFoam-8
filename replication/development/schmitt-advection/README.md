# Pure-oxygen contact advection at 6 MPa (`schmitt2020-fig-5`)

Status: **diagnostic working, comparison partly resolved.** The scheme now advects the interface
without blowing up and reproduces the magnitudes of the reference figure's spurious pressure and
velocity waves; the density profile diffuses more than the reference shows, and the interface
width the target does not state is inferred.

## What the registered target asks for

`schmitt2020-fig-5` states: p about 6 MPa, a density interface from 1000 to 100 kg/m3 with an
error-function profile, a uniform velocity of 10 m/s, dx = 0.01 m, refinement factors 2, 4, 6 and
t = 20 ms. Its four panels are density, temperature, pressure and velocity along the domain. The
density and temperature panels are the same statement in two variables - a dense cold state and a
light warm one in pressure equilibrium - and the scientific content is in the pressure and
velocity panels, where an inconsistent discretisation produces spurious oscillations across the
interface while a consistent one leaves both flat.

The reference image is `assets/schmitt2020-fig-5-paper.png`; the conditions above are the whole of
the text available here, so the shape of the error-function profile (half-width 0.02 m) and the
mapping of "n_x = 2, 4, 6" onto grid refinement are **inferred**, and are declared as such.

## The initial condition is not imposed on temperature

`schmitt_advection.py` builds the initial condition in the variables the target gives: p = 6 MPa
and u = 10 m/s everywhere, with the density following the error function. Temperature is **not**
imposed; it is the temperature at which SRK oxygen has that density at 6 MPa, which lands on
117.11 K at 1000 kg/m3 and 248.90 K at 100 kg/m3 - the two ends of the paper's temperature panel
(115 and 250 K). That agreement is a property of the equation of state, not of a fit, and the
sound speed follows without tuning: 630.1 m/s at the dense end, 335.8 m/s at the light end, with
the near-critical dip to 284.4 m/s at 400 kg/m3 where gamma reaches 22.

Thermodynamics are Soave-Redlich-Kwong for pure oxygen with the Chung et al. (1988) dense-gas
viscosity and thermal conductivity, taken from `../cavalieri-properties/srk_chung.py` so the
equation of state is covered by that module's tests instead of a second copy. The caloric
departures are evaluated from the molar volume that belongs to the cell's density rather than by
re-solving the cubic at (T, p), because a (T, p) call can return a different branch than the
density implies when the cubic has several stable roots.

## The scheme

- **Flux**: HLLC with the SRK sound speed. The contact-preserving member of the HLL family: for
  two states that share a pressure and a velocity the star speed equals that velocity and the flux
  reduces exactly to the upwind flux, so a contact carries no dissipation at all.
  `test_hllc_reproduces_the_upwind_flux_for_a_pressure_equilibrium_contact` measures that to 1e-12
  for the strongest jump in the run.
- **Reconstruction**: MUSCL/minmod on (rho, u, p), with the temperature of each reconstructed
  state recovered from its density and pressure by a guarded Newton (2-4 iterations from the cell
  temperature). Reconstructing temperature instead pairs a density slope with a temperature slope
  and manufactures a pressure jump where the field has none; reconstructing (rho, u, p) leaves a
  uniform pressure uniform, which
  `test_reconstructing_density_and_pressure_leaves_a_uniform_pressure_uniform` pins.
- **Diffusion**: central viscous and conductive fluxes; explicit Euler with an adaptive acoustic
  and diffusive step at CFL 0.30.
- **Boundaries**: fixed inflow at the dense far-field state on the left, zero-gradient on the
  right. A periodic domain is not used: a single interface cannot be periodic, and the seam
  becomes a spurious shock (a first attempt measured L2 = 135 kg/m3 on it).
- **Conservation certificate**: the change in the domain totals must equal the boundary flux
  integrals. Every run reports the residual; it is about 1e-15 relative in all runs below, which
  is why mass grows by 0.75 while the interface crosses the domain - the inflow is counted.

## Two defects that were found and fixed here

Both were silent: each rejected admissible states without saying so, and each now has a test.

1. **The caloric inversion was bracketed in the wrong place.** The window started just above the
   positive-pressure floor, but SRK's liquid-branch departure enthalpy gives the internal energy a
   minimum about thirty kelvin higher, in the pseudo-boiling band, so states between the two were
   reported as outside the admissible range - a 10 kJ/kg band, which is the size of a single
   first-step update.
2. **The minimum search itself could land on the repulsive branch.** Mechanical stability
   (`dp/dv < 0`) is required, not only `p > 0`: below that limit the cubic's repulsive root solves
   the same energy equation, and at 100 kg/m3 it gave a spurious 94.6 K inversion against the
   physical 248.9 K. The minimum is now searched over mechanically stable states only, one table
   in log density, built once per process.

A third property of the equation of state shapes everything below: in the pseudo-boiling band the
admissible energy band above the minimum is narrow - 3.8 kJ/kg at 400 kg/m3 - so a smeared contact
leaves it quickly. That is a property of SRK oxygen at 6 MPa, not of the discretisation.

## What the disagreement with the first flux was

The first version used Rusanov (local Lax-Friedrichs), and the measured reason it cannot work is
in the conserved formulation: SRK oxygen carries a ~240 kJ/kg internal-energy offset between the
two ends of the interface, so a dissipation term proportional to the conserved-energy jump and to
the acoustic speed is about **31 times** the physical advective energy flux across a one-cell step
(`test_rusanov_dissipation_dominates_at_a_one_cell_interface`). The retained run
`runs/rusanov-order1-dx0.02/` shows what that does at the paper's time: pressure to 7.8 MPa above
ambient, velocity from -54 to +24 m/s, 29 368 clamped cell-steps and no interface crossing at all,
while the conservation residual stays at 1e-16. A conservative update is not by itself evidence of
a correct solution, which is why the certificate is reported next to the amplitudes rather than
instead of them.

`runs/order1-dx0.02/` is the same failure from a **superseded** version of the module, kept only
to show what the defect of the energy window looked like from outside; it is not reproducible from
the current source and the test that pins a negative control now reads
`runs/rusanov-order1-dx0.02/`.

## Resolution study and the reference panels

t = 4 ms, 6 MPa, u = 10 m/s, density 1000 -> 100 kg/m3, order 2, HLLC:

| dx [m] | cells across the interface | steps | p amplitude | u amplitude | interface travel [m] | L2 [kg/m3] | clamped cells |
|---|---|---|---|---|---|---|---|
| 0.020 | 1 | 427 | 8.99e-2 | 7.90e-1 | 0.0449 | 30.2 | 0 |
| 0.010 | 2 | 854 | 1.93e-2 | 1.77e-1 | 0.0426 | 12.0 | 0 |
| 0.005 | 4 | 1707 | 4.12e-3 | 4.02e-2 | 0.0411 | 4.34 | 0 |
| 0.0025 | 8 | 3415 | 9.00e-4 | 8.74e-3 | 0.0403 | 1.30 | 0 |

The spurious amplitudes fall by 4.65, 4.69 and 4.58 per halving of dx (observed order 2.2), the
interface travels to 0.040-0.045 m against the exact 0.040 m, the minimum density stays at or
above 99.87 kg/m3 and rises towards 100 as the grid is refined, no cell is clamped, and the
conservation residuals are 1e-15 or better. At eight cells across the interface the pressure
stays within 0.09 % of ambient.

The full-time run, dx = 0.005 m, t = 20 ms (8 535 steps):

| quantity | computed | reference panel |
|---|---|---|
| pressure range | 5.9753 to 6.0000 MPa, i.e. 0.41 % below ambient | 0.33 % oscillations, positive and negative |
| velocity range | 9.562 to 10.042 m/s, i.e. a 4.4 % dip | dips to 9.5 m/s, i.e. 5 % |
| density range | 99.87 to 999.97 kg/m3 | 100 to 1000 |
| temperature range | 117.10 to 248.78 K | 115 to 250 K |
| interface travel after 20 ms | 0.2035 m against the exact 0.2000 m | the interface reaches about x = 0.4 m |
| L2 / Linf density error against the translated initial profile | 15.0 / 89.4 kg/m3 | not quantified in the figure |
| clamped cells, conservation residual | 0, 2e-15 | - |

So the *magnitudes* of the two artifacts the figure is about are reproduced to within about a
quarter of each other - the pressure oscillation to 0.41 % against 0.33 %, the velocity dip to
4.4 % against 5 % - while the density profile is **more diffused** than the reference shows
(Linf 89 kg/m3 at the steepest part of the profile, i.e. the transition is spread over more cells
than the initial condition had).

## What is declared unresolved

- **The interface width is inferred, and it sets the answer.** With an inferred half-width of
  0.02 m, the paper's own dx = 0.01 m resolves the interface with two cells and gives a 1.9 %
  pressure amplitude, not 0.41 %. The amplitudes above are therefore a statement about cells
  across the interface, not about the paper's grid; reaching the reference magnitudes needs four
  cells, which for this half-width is dx = 0.005 m. The target text does not give the profile
  width.
- **The mapping of `n_x = 2, 4, 6` onto refinement is inferred** as refinement factors of the
  dx = 0.01 m base grid, which is how the three grids above were chosen.
- **The paper's schemes are not identified here.** The reference's four curves are scheme and
  resolution variants; this module has one scheme at three resolutions, so the curves are
  compared by magnitude, not point by point.
- **No figure is bound yet.** Nothing here has been rendered against the reference panels; the
  numbers above are the module's own and the figure contract is a separate step.
- The density profile's diffusion is measured but not yet explained cell by cell; minmod clipping
  at the interface (the steepest cell has no admissible slope) is the obvious candidate and has
  not been tested separately.

## Reading the runs

`python3 schmitt_advection.py --out DIR --dx 0.01 0.005 --t-end 0.02 --order 2` (add
`--flux rusanov` for the negative control). Costs measured here: dx = 0.005 m to t = 20 ms took about 13 minutes of one core; the t = 4 ms
resolution study above is about 12 minutes in total, most of it in the dx = 0.0025 m point.
`runs/rusanov-order1-dx0.02/run-dx-0.02.json` is the negative control, and
`runs/order1-dx0.02/` its superseded predecessor.
