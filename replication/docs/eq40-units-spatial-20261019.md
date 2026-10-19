# Equation (40): meaning, units and spatial evaluation

19 October 2026. Rechecked the supplied Nguyen 2022 PDF visually on page 11,
Section 5.3 and Eq.(40), and Section 4.2 Eqs.(37) and (39). The paper uses a
local OH-isoline displacement speed after the ignition transient has decayed.
It does not prescribe a spatial integral, a particular OH level, or the use of
OpenFOAM's timestep-averaged chemistry source.

`Sd_star = (omega_OH - div(rho*YOH*V_OH)) / (rho_u*|grad(YOH)|)`.

| Symbol | Physical meaning | SI units | Implementation |
| --- | --- | --- | --- |
| YOH | OH mass fraction, not mole fraction | kg/kg, dimensionless | OH field; 2e-5 is 20 ppm by mass, not ppm by mole |
| grad(YOH) | Spatial gradient of mass fraction | 1/m | fvc::grad on the physical mesh; magnitude only in denominator |
| rho | Local mixture density | kg/m3 | Real-fluid thermodynamics |
| rho_u | Unburned mixture density | kg/m3 | Separate fresh-gas average on each outer 5% of the domain; initial value also retained |
| V_OH | Diffusion velocity relative to mixture velocity | m/s | Distinct from bulk gas U and front propagation velocity |
| j_OH=rho*YOH*V_OH | Diffusive OH mass flux | kg/(m2 s) | Flux, not production rate |
| -div(j_OH) | Diffusive contribution to local OH production | kg/(m3 s) | Positive when diffusion supplies OH locally |
| omega_OH | Signed net OH mass production by chemistry | kg/(m3 s) | RR(OH), already mass-based; not Qdot, concentration rate, or a finite-volume matrix source |
| Sd_star | Density-weighted local displacement speed | m/s | Multiply by 100 once for figures in cm/s |

Dimensional check: `(kg m^-3 s^-1)/(kg m^-3 * m^-1) = m/s`.
There is no extra multiplication by molecular weight, division by density,
or multiplication/division by cell volume in the implemented quotient. Local
displacement speed Sd uses local rho in the denominator; the paper's weighted
quantity is `(rho/rho_u)*Sd`, hence directly uses rho_u. Do not apply that density
weight a second time. Keep the numerator signed; taking its absolute value would
hide local retreat/relaxation. At zero OH gradient the isoline speed is undefined.

## Source meanings in this code

The custom chemistry constructor gives RR dimensions mass/volume/time.
calculate() forms concentrations `c=rho*Y/W` in kmol/m3 and assigns
`RR_i=(dc_i/dt)*W_i`, with W in kg/kmol. Thus its result is already the mass
production rate required by Eq.(40). solve(deltaT) instead assigns
`RR_i=(c_i,end-c_i,start)*W_i/deltaT`: the local chemistry-step average.
Integrated here means integrated in time within one cell, never integrated
across the flame or over the domain. Neither quantity is the heat-release field.

The instantaneous-state source is the direct constitutive interpretation of
the continuum formula. The averaged source remains useful because it is what
the discrete species equation consumed. Agreement of the latter with a plotted
paper value is not a reason to prefer it. The paper does not disclose whether
its implementation sampled stored integrated RR or recomputed instantaneous
rates, so that implementation choice cannot be attributed to the authors.

The mesh uses metres (convertToMeters 1), dx=5e-7 m, physical pressure
10132500 Pa (=100 atm), and unburned T=298 K. The initial unburned real-fluid
density is 112.799848885 kg/m3. Our 1e-5/2e-5/3e-5 OH levels are declared
diagnostic choices; the paper specifies OH but no numerical level.
Figure 12 was also checked visually on page 13: its ordinate is explicitly
cm/s. Thus the plotted reference near 6.8 cm/s corresponds to about 0.068 m/s.
The transport implementation's Dimix() explicitly returns its correlation value
divided by 1e4, converting cm2/s to m2/s. No additional diffusivity conversion is
applied in the diagnostic.

## Diffusion definition to compare

Paper Eq.(39) states `V_k=-D_k/X_k * grad(X_k)`. With
`X_k=Y_k*Wmix/W_k`, it gives

`-div(j_k) = div(rho*D_k*grad(Y_k))
             + div(rho*D_k*Y_k/Wmix*grad(Wmix))`.

These are the ordinary and molecular-weight terms. The paper describes setting
the last species' flux from the zero-net-diffusion constraint. The deployed OH
equation additionally subtracts two all-species mixture-flux correction terms.
We therefore report both the literal two-term Eq.(39) evaluation and the deployed
four-term spatial operator. This identifies a constitutive/operator distinction;
it does not prove how the unpublished publication binary assembled diffusion.
The diffusion terms at the species-solve stage are also sequential/lagged,
whereas the instantaneous evaluation uses a common final state.

## Spatial audit protocol

Donor job 124864929 remains active and read-only. Analysis job 124870644 uses
source a438f6414a1d2820cbc3de3c0a4d3336afa434db on draft/spatial-speed.
It copies the eight-rank checkpoints at 20.0025485065, 39.9834968798,
59.9834968798 and 79.9834968798 us. For each, it exports instantaneous terms at
the reloaded state, then takes one isolated 100 ns step and exports source-used
and instantaneous end-step terms. This cannot reconstruct an unsaved historical
RR field; replay output is labelled as replay output.

A baseline one-step replay from the first checkpoint uses qualified native
solver 124868494. All original written fields must match before treating the
spatial exporter as nonintrusive. Checkpoint contour values are also compared
with the original in-situ history at matching times. Plot full profiles and
mark the actual OH isolines; exclude vanishing-gradient values explicitly.

## Observed spatial results

Job 124870644 completed in 6 min 43 s, exit 0. All 1,360 original written
numerical field bodies matched the baseline replay. Twelve full-domain profiles
contain 8,000 finite rows each. Executable SHA-256:
e3ef56491e44c2dfdd79826805f992ed8220901643ac14554c38ca8e81e6b385.
The downloaded archive SHA-256 is
f3c3d29ca5bf2214690e90e0f912d93ac969bbb37d202be58bdb5ca1e1cdf5a1.
Recomputed checkpoint contour speeds differ from the live instantaneous history
by at most 0.000291 cm/s across both fronts and all three OH levels.

| Checkpoint (us) | Instantaneous S*d at YOH=1e-5 | At 2e-5 | At 3e-5 | Two-term Fick value at 2e-5 |
| --- | ---: | ---: | ---: | ---: |
| 20.0025 | 113.762 | 1.133 | -68.996 | 1.116 |
| 39.9835 | 135.108 | 10.614 | -75.243 | 10.603 |
| 59.9835 | 143.025 | 23.733 | -59.022 | 23.724 |
| 79.9835 | 143.874 | 26.985 | -53.915 | 26.978 |

Values are cm/s on the left fresh-side OH flank. There is no marker-independent
plateau over these chosen levels. The negative values are retained, not made
positive or discarded to obtain agreement with Figure 12. The two diffusion
definitions differ by only 0.00744 cm/s at the latest primary contour; that
correction does not explain the roughly 21 cm/s difference from the source-used
estimate. The instantaneous chemistry varies sharply across this thin OH layer.

A worked dimensional check at 79.9835 us, YOH=2e-5:

- omegaOH = -468.899688 kg/(m3 s);
- minusDivJOH = 828.361545 kg/(m3 s);
- rho_u = 112.796656 kg/m3;
- |grad(YOH)| = 11.8094771 1/m;
- S*d = 359.461857 / (112.796656 * 11.8094771) = 0.269852175 m/s
  = 26.9852175 cm/s.

The fresh-density change from its initial value is at most about 0.05% in these
snapshots, so initial-versus-current rho_u cannot account for the discrepancy.
At the 80.0835-us replay endpoint the source-used result is 5.729 cm/s, composed
of -56.244 cm/s chemistry and +61.972 cm/s diffusion; instantaneous end-step
chemistry instead gives 27.189 cm/s. These are local contributions, not integrals.

The 20-us one-step replay gives 13.524 cm/s using the averaged source; it must
not be substituted for the original uninterrupted history. Equality with a
baseline restart qualifies the exporter, not recovery of unsaved chemistry
substep history. Checkpoint instantaneous evaluations are the validated direct
spatial comparison; the isolated replay is a separate diagnostic.

The OH=1e-5 to 3e-5 interval occupies only 1.76–1.86 um (about 3.5–3.7 cells).
A thermal-thickness estimate `(Tmax-Tu)/max|dT/dx|` increases from 16.86 to
19.27 um, about 34–39 cells. The paper does not define its thickness measure,
so these counts are not proof of a specific mesh mismatch; they do establish
why radical-layer interpolation and refinement need checking. At the latest
primary contour, interpolating cellwise speed gives 30.717 cm/s, versus 26.985
when interpolating source/diffusion/gradient before forming the quotient.
The diagnostic and displayed curves consistently use the latter. The plot
interpolation does not create additional physical resolution.

Decision: retain instantaneous Eq.(40) as the direct continuum-formula comparison
and keep the averaged-source result as a discrete-solver diagnostic. Neither is
an accepted laminar flame speed. The next numerical check should separate
chemistry/timestep effects from spatial interpolation with controlled smaller
timesteps and then a finer grid, without selecting an OH level to fit 6.8 cm/s.
Figures and raw contour tables are in output/spatial-speed-20261019-v2; code and
all assumptions are in development/premixed-spatial.
