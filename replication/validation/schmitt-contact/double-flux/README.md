# Design: one-dimensional real-fluid double-flux candidate

**Experimental candidate; six fresh20ms numerical controls completed.**
R20 job128022863/sourcec6d486e rebuilt the complete custom runtime and completed
all published widths. Numerical startup/closure checks passed; paper profiles
remain too diffuse and energy defects are explicitly reported. This is not
scientific acceptance or reacting-G2 qualification. See the retained
[run record](../../../runs/20261114-parallel-g2-baseline/README.md).

This experimental OpenFOAM application tests pressure-equilibrium preservation
on the six nonreacting Schmitt2020 Figures5/6 contacts. It uses the executing
SRK Chung thermophysical library, H2/O2 composition and actual OpenFOAM fields.
It is not a general multidimensional reacting/FGM solver or a claimed repair to
reactingFoamSolveZ. Original PIMPLE results remain the baseline.

The finite-volume HLLC double-flux formulation follows Ma, Lv and Ihme2017 and
the authors' DoubleFlux-1D supplementary code. Mass, momentum and species use
common face fluxes. Energy flux uses each receiving cell's frozen thermodynamic
tangent. SSP-RK3 advances one timestep; true-EOS synchronization then records
its energy defect explicitly. First-order face states are the initial candidate;
this differs from Schmitt's TTGC/nonconservative artificial viscosity. Keep the
attribution and BSD2 notice in NOTICE.md with source/binary redistributions.

Inputs: a fresh serial uniform one-dimensional x mesh, p/U/T/H2/O2 fields and
exact SRK Chung thermo dictionary, with the existing contact initializer already
executed at time0. Controls: maxAcousticCo (default0.3), maxDeltaT, endTime and
ordinary sampling/writes. No chemistry, PDF, turbulence, transport diffusion,
parallel decomposition or CFD restarts are supported. All other models/states
must be rejected explicitly, not silently substituted.

Outputs: transported rho/U/Y, pressure from the frozen double-flux update,
true-EOS T/h at that density/pressure/composition, sampled profiles and signed
mass/momentum/energy balance records. Each true-EOS density inversion must agree
with transported density within1e-8. All caloric identities remain required;
quasi-conservative energy synchronization is a reported algorithmic defect,
never described as exact total-energy conservation or scientific acceptance.

Dependencies: OpenFOAM8 finite-volume/mesh libraries and the frozen full-fork
reaction/fluid/specie runtime. The temperature projection analytically inverts
the executing SRK a(T) coefficient representation at fixed p/rho; acoustic speed
uses the same coefficients with actual mixture Cp/Cv. No EOS coefficients,
reaction rates or reference curves are fitted. No network access or secrets.
Caller wrappers supply isolated build/output paths and exact library identities.

Build inside Slurm with wmake. Run -help, then a fresh uniform-state control,
a short oxygen interface, and all six fresh20ms contacts. Compare pressure and
velocity equilibrium, actual EOS closure, conservation defects and profiles
against the retained PIMPLE baseline and original figures. A normal exit or
flat pressure alone does not qualify the method. Later G2 integration needs a
separate multidimensional reacting formulation and its own validation.

Common HLLC waves use actual SRK acoustic speeds, while receiving-cell energy
fluxes use frozen tangents. This adaptation differs from the reference MATLAB
wave estimates and requires the stated physical controls. Far-field inlet
ghosts are fixed initial states and outflow ghosts extrapolate the last cell;
this is not AVBP NSCBC. Diffusion is explicitly disabled via contactDFInviscid
yes, even though the shared input dictionary retains its Fourier declaration.
The caloric audit runs after intentional true-EOS energy synchronization; its
passing cannot be presented as evidence of conservative energy transport.

Use configure.mjs FRESH_CASE END_TIME [--uniform] for a read-only plan; add
--apply inside Slurm before the existing density initializer. Uniform mode
sets150K pure oxygen at6MPa without copying any CFD state. Configuration records
all changed input hashes and explicitly selects inviscid double flux. The
normal six inputs retain their original densities, composition and temperatures.

Numerical startup qualification checks completed time, EOS/caloric closure,
pressure/velocity equilibrium and mass/budget residuals. For a uniform state
only, energy-defect magnitude must also remain at roundoff scale. Interface
energy defects are recorded for review, not declared conservative or accepted.

Link the three custom libraries by explicit FOAM_USER_LIBBIN paths. Bare -l
lookup can select stock OpenFOAM libraries ahead of the fork despite -L order,
causing missing rfSpecie symbols or mixed ABI. The build receipt must verify
resolved real paths and hashes before a physical run.


## Limited-linear spatial diagnostic

`configure.mjs FRESH_CASE END_TIME --muscl [--apply]` selects
`contactDFReconstruction limitedLinear`; default `firstOrder` is unchanged.
The new reconstruction uses a monotonized-central slope on density, velocity,
pressure, acoustic speed and H2 mass fraction; O2 is its exact complement.
The cell-owned frozen gamma/e0 are not reconstructed. Each SSPRK stage still
projects through the executing SRK model and retains existing range, closure
and species checks. No species clipping, EOS fit or acceptance-limit change.

This is a MUSCL/SSPRK accuracy experiment, not a claimed implementation of the
full entropy-stable hybrid method in Ma et al.2017. Reconstructing the acoustic
speed from valid cell states is a wave-speed estimate; face states are not
claimed independently EOS-qualified. Scope remains nonreacting 1D contacts.
Inputs/outputs, boundaries, secret handling and dependencies remain as above.
Verify actual uniform-state roundoff, short controls, then all six fresh20ms
profiles and budgets. Re-run first-order oxygen/mixed anchors as controls, and
compare interface width, pressure/velocity equilibrium and explicit energy
defects. A sharper plot alone does not qualify a reacting solver.
